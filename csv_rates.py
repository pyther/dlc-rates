#!/usr/bin/env python3
"""
csv_rates.py — build combined flat and TOU rate tables from normalized
tariff-component source files.

Each source file only records a value at the point it actually changes,
keyed by whatever it genuinely varies on:

    data/riders.csv             Effective Date, Rider 1, Rider 5, Rider 15a, Rider 10 (%)
                                 varies by date only

    data/distribution_base.csv  Effective Date, Class, Season, Base Rate
                                 varies by class + season

    data/transmission.csv       Effective Date, Class, Transmission
                                 varies by class

    data/supply.csv             Effective Date, Rate
                                 flat PTC supply charge, varies by date only

    data/supply_tou.csv         Effective Date, Period, Rate
                                 TOU PTC supply charge, varies by period

At build time, every output row is produced by looking up the most recent
("as of") value for each component independently and summing them. Adding
a new tariff supplement means appending exactly one row to whichever file
changed — never touching the others.

Writes:
    output/rates.csv   Class, Season, Effective Date, Rate Type, Total, PTC, Distribution
"""

import csv
from datetime import date
from pathlib import Path

DATA = Path("data")
OUTPUT = Path("output")

CLASSES = ["RS", "RH", "RA"]
TOU_PERIODS = ["Peak", "Off-Peak", "Super Off-Peak"]


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_date(s):
    return date.fromisoformat(s.strip())


def parse_num(s):
    return float(s.strip())


def load_riders():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Rider 1": parse_num(r["Rider 1"]),
            "Rider 5": parse_num(r["Rider 5"]),
            "Rider 15a": parse_num(r["Rider 15a"]),
            "Rider 10 (%)": parse_num(r["Rider 10 (%)"]),
            "Rider 22 (%)": parse_num(r["Rider 22 (%)"]),
        }
        for r in load(DATA / "riders.csv")
    ]


def load_distribution_base():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Class": r["Class"],
            "Season": r["Season"],
            "Base Rate": parse_num(r["Base Rate"]),
        }
        for r in load(DATA / "distribution_base.csv")
    ]


def load_transmission():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Class": r["Class"],
            "Transmission": parse_num(r["Transmission"]),
        }
        for r in load(DATA / "transmission.csv")
    ]


def load_supply():
    return [
        {"Effective Date": parse_date(r["Effective Date"]), "Rate": parse_num(r["Rate"])}
        for r in load(DATA / "supply.csv")
    ]


def load_supply_tou():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Period": r["Period"],
            "Rate": parse_num(r["Rate"]),
        }
        for r in load(DATA / "supply_tou.csv")
    ]


def as_of(rows, target_date, **filters):
    """Most recent row on or before target_date matching all filters, or None."""
    candidates = [
        r for r in rows
        if r["Effective Date"] <= target_date
        and all(r[k] == v for k, v in filters.items())
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r["Effective Date"])


def distribution_total(dist, riders, target_date, cls, season):
    base_row = as_of(dist, target_date, Class=cls, Season=season)
    rider_row = as_of(riders, target_date)
    if base_row is None or rider_row is None:
        return None

    # 1. Base distribution subtotal
    subtotal = (
        base_row["Base Rate"]
        + rider_row["Rider 1"]
        + rider_row["Rider 5"]
        + rider_row["Rider 15a"]
    )

    # 2. Apply DSIC (Rider 22) to the subtotal
    # (Dividing by 100 because the CSV stores it as 2.17 instead of 0.0217)
    with_dsic = subtotal * (1 + rider_row["Rider 22 (%)"] / 100)

    # 3. Apply STAS (Rider 10) on top of the DSIC-inflated total
    final_total = with_dsic * (1 + rider_row["Rider 10 (%)"] / 100)

    return final_total


def flat_components(supply, trans, target_date, cls):
    """Returns (supply_rate, transmission_rate) or None if not yet in effect."""
    supply_row = as_of(supply, target_date)
    trans_row = as_of(trans, target_date, Class=cls)
    if supply_row is None or trans_row is None:
        return None
    return supply_row["Rate"], trans_row["Transmission"]


def tou_components(supply_tou, trans, target_date, cls, period):
    """Returns (supply_rate, transmission_rate) or None if not yet in effect."""
    supply_row = as_of(supply_tou, target_date, Period=period)
    trans_row = as_of(trans, target_date, Class=cls)
    if supply_row is None or trans_row is None:
        return None
    return supply_row["Rate"], trans_row["Transmission"]


def get_season(target_date):
    """Season is a fixed calendar rule, not a filed tariff value."""
    return "Summer" if 5 <= target_date.month <= 10 else "Winter"


def seasons_for_class(dist, cls):
    return {r["Season"] for r in dist if r["Class"] == cls}


def is_seasonal(dist, cls):
    return seasons_for_class(dist, cls) != {"All"}


def season_transition_dates(start_year, end_year):
    """Every May 1 / Nov 1 in range — the dates Distribution can change on
    for seasonal classes even with no new tariff filing."""
    dates = set()
    for year in range(start_year, end_year + 1):
        dates.add(date(year, 5, 1))
        dates.add(date(year, 11, 1))
    return dates


def timeline_for(dist, riders, trans, supply, supply_tou, cls, as_of_today):
    """Union of every date any relevant component changed for this class,
    plus calendar season-transition dates if the class has seasonal rates.
    Never projects past as_of_today — a season flip that hasn't happened
    yet shouldn't appear until the day it actually occurs."""
    dates = set()
    dates |= {r["Effective Date"] for r in dist if r["Class"] == cls}
    dates |= {r["Effective Date"] for r in riders}
    dates |= {r["Effective Date"] for r in trans if r["Class"] == cls}
    dates |= {r["Effective Date"] for r in supply}
    dates |= {r["Effective Date"] for r in supply_tou}

    if is_seasonal(dist, cls) and dates:
        dates |= season_transition_dates(min(d.year for d in dates), as_of_today.year)

    return sorted(d for d in dates if d <= as_of_today)


def build_tables(as_of_today):
    riders = load_riders()
    dist = load_distribution_base()
    trans = load_transmission()
    supply = load_supply()
    supply_tou = load_supply_tou()

    flat_rows = []
    tou_rows = []

    for cls in CLASSES:
        seasonal = is_seasonal(dist, cls)
        timeline = timeline_for(dist, riders, trans, supply, supply_tou, cls, as_of_today)

        for dt in timeline:
            season = get_season(dt) if seasonal else "All"
            distribution = distribution_total(dist, riders, dt, cls, season)
            if distribution is None:
                continue  # no distribution data yet in effect for this class/season
            distribution = round(distribution, 4)

            flat = flat_components(supply, trans, dt, cls)
            if flat is not None:
                supply_rate, transmission_rate = flat
                total = round(distribution + supply_rate + transmission_rate, 4)
                flat_rows.append((dt, cls, season, distribution, supply_rate, transmission_rate, total))

            for period in TOU_PERIODS:
                tou = tou_components(supply_tou, trans, dt, cls, period)
                if tou is None:
                    continue  # TOU pilot data not yet in effect on this date
                supply_rate, transmission_rate = tou
                total = round(distribution + supply_rate + transmission_rate, 4)
                tou_rows.append((dt, cls, season, period, distribution, supply_rate, transmission_rate, total))

    return flat_rows, tou_rows


def write_output(flat_rows, tou_rows):
    OUTPUT.mkdir(exist_ok=True)

    # Class ascending (RA, RH, RS), Effective Date descending (newest first)
    # within each class. Two stable sorts, least-significant key first.
    flat_sorted = sorted(flat_rows, key=lambda r: r[0], reverse=True)  # date desc
    flat_sorted = sorted(flat_sorted, key=lambda r: r[1])              # class asc

    with open(OUTPUT / "rates.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Effective Date", "Class", "Season", "Distribution Rate", "Supply Rate",
                    "Transmission Rate", "Total Rate"])
        for row in flat_sorted:
            w.writerow(row)

    # New: TOU rates, same shape plus a Period column. Not yet wired into
    # generate_json.py / html_rates.py — kept separate until we know how
    # TOU currently reaches the site.
    # Class ascending, Effective Date descending, Period in the fixed
    # Off-Peak / Peak / Super Off-Peak display order (not alphabetical).
    period_order = {"Off-Peak": 0, "Peak": 1, "Super Off-Peak": 2}
    tou_sorted = sorted(tou_rows, key=lambda r: period_order[r[3]])  # period, fixed order
    tou_sorted = sorted(tou_sorted, key=lambda r: r[0], reverse=True)  # date desc
    tou_sorted = sorted(tou_sorted, key=lambda r: r[1])                # class asc

    with open(OUTPUT / "rates_tou.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Effective Date", "Class", "Season", "Period", "Distribution Rate", "Supply Rate",
                    "Transmission Rate", "Total Rate"])
        for row in tou_sorted:
            w.writerow(row)


if __name__ == "__main__":
    flat_rows, tou_rows = build_tables(date.today())
    write_output(flat_rows, tou_rows)
    print(f"Wrote {OUTPUT / 'rates.csv'} ({len(flat_rows)} rows)")
    print(f"Wrote {OUTPUT / 'rates_tou.csv'} ({len(tou_rows)} rows)")
