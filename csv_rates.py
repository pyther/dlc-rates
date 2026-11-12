#!/usr/bin/env python3
"""
csv_rates.py — build combined flat and TOU rate tables from normalized
tariff-component source files.

Each source file only records a value at the point it actually changes,
and every row names the tariff supplement that set it (Source column;
left blank where the supplement isn't known yet). Supplements are listed
in data/tariffs.csv.

    data/tariffs.csv            Supplement, Issued, Effective Date, Changes, Document

    data/distribution_base.csv  Effective Date, Class, Season, Base Rate, Source
                                 ¢/kWh, varies by class + season

    data/riders.csv             Effective Date, Rider, Value, Unit, Source
                                 one row per rider change; Unit is ¢/kWh or %

    data/transmission.csv       Effective Date, Class, Transmission, Source
                                 ¢/kWh (Appendix A), varies by class

    data/supply.csv             Effective Date, Rate, Source
                                 flat default supply charge (Rider 8), ¢/kWh

    data/supply_tou.csv         Effective Date, Period, Rate, Source
                                 TOU supply charge (Rider 8), varies by period

At build time, every output row is produced by looking up the most recent
("as of") value for each component independently and summing them. Adding
a new tariff supplement means adding one row to tariffs.csv plus one row
per value it changed — never touching the others.

Rider No. 1 (Retail Market Enhancement Surcharge) is a per-customer monthly
charge (currently $0), not a per-kWh charge, so it isn't part of the rate.

Writes:
    output/rates.csv       Class, Season, Effective Date, Rate Type, Total, PTC, Distribution
    output/rates_tou.csv   same, plus Period
"""

import csv
import re
import sys
from datetime import date, timedelta
from pathlib import Path

DATA = Path("data")
OUTPUT = Path("output")

ARCHIVE_URL = "https://tariffs.pyther.net/tariff-25/"
DOC_PATTERN = re.compile(r"dlc-tariff-25-(supp-)?(\d+)\.pdf")

CLASSES = ["RS", "RH", "RA"]
TOU_PERIODS = ["Peak", "Off-Peak", "Super Off-Peak"]

# Riders that make up the per-kWh distribution rate, with their units.
RIDERS = {
    "Rider 5": "¢/kWh",   # Universal Service Charge
    "Rider 15A": "¢/kWh", # Energy Efficiency and Conservation Surcharge
    "Rider 22": "%",      # Distribution System Improvement Charge (DSIC)
    "Rider 10": "%",      # State Tax Adjustment Surcharge (STAS)
}
RIDER_LABELS = {
    "Rider 5": "Universal Service Charge (Rider 5)",
    "Rider 15A": "Energy efficiency surcharge (Rider 15A)",
    "Rider 22": "DSIC (Rider 22)",
    "Rider 10": "State tax adjustment (Rider 10)",
}


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_date(s):
    return date.fromisoformat(s.strip())


def parse_num(s):
    return float(s.strip())


def source(r):
    return (r.get("Source") or "").strip()


def load_tariffs():
    """Supplements, keyed by number. Document is the archive file holding the
    supplement's pages: its own filing (dlc-tariff-25-supp-N.pdf) or a full
    tariff as of supplement N or later (dlc-tariff-25-N.pdf)."""
    tariffs = {}
    for r in load(DATA / "tariffs.csv"):
        num, docname = r["Supplement"].strip(), r["Document"].strip()
        m = DOC_PATTERN.fullmatch(docname)
        if not m:
            sys.exit(f"tariffs.csv: Supplement {num}: document {docname!r} doesn't match "
                     "dlc-tariff-25-N.pdf or dlc-tariff-25-supp-N.pdf")
        is_supp, doc_num = bool(m.group(1)), int(m.group(2))
        if (is_supp and doc_num != int(num)) or (not is_supp and doc_num < int(num)):
            sys.exit(f"tariffs.csv: Supplement {num} can't be found in {docname}")
        tariffs[num] = {
            "Supplement": num,
            "Effective Date": parse_date(r["Effective Date"]),
            "Changes": r["Changes"].strip(),
            "URL": ARCHIVE_URL + docname,
        }
    return tariffs


def load_riders():
    rows = []
    for r in load(DATA / "riders.csv"):
        name, unit = r["Rider"].strip(), r["Unit"].strip()
        if RIDERS.get(name) != unit:
            sys.exit(f"riders.csv: unknown rider or unit: {name!r} {unit!r}")
        rows.append({
            "Effective Date": parse_date(r["Effective Date"]),
            "Rider": name,
            "Value": parse_num(r["Value"]),
            "Source": source(r),
        })
    return rows


def load_distribution_base():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Class": r["Class"],
            "Season": r["Season"],
            "Base Rate": parse_num(r["Base Rate"]),
            "Source": source(r),
        }
        for r in load(DATA / "distribution_base.csv")
    ]


def load_transmission():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Class": r["Class"],
            "Transmission": parse_num(r["Transmission"]),
            "Source": source(r),
        }
        for r in load(DATA / "transmission.csv")
    ]


def load_supply():
    return [
        {"Effective Date": parse_date(r["Effective Date"]), "Rate": parse_num(r["Rate"]), "Source": source(r)}
        for r in load(DATA / "supply.csv")
    ]


def load_supply_tou():
    return [
        {
            "Effective Date": parse_date(r["Effective Date"]),
            "Period": r["Period"],
            "Rate": parse_num(r["Rate"]),
            "Source": source(r),
        }
        for r in load(DATA / "supply_tou.csv")
    ]


def load_all():
    return {
        "tariffs": load_tariffs(),
        "riders": load_riders(),
        "dist": load_distribution_base(),
        "trans": load_transmission(),
        "supply": load_supply(),
        "supply_tou": load_supply_tou(),
    }


def validate_sources(tables):
    """Every Source must be a supplement in tariffs.csv with the same
    effective date. Returns the number of rows with no Source yet."""
    tariffs = tables["tariffs"]
    missing = 0
    for name in ("riders", "dist", "trans", "supply", "supply_tou"):
        for r in tables[name]:
            s = r["Source"]
            if not s:
                missing += 1
                continue
            if s not in tariffs:
                sys.exit(f"{name}: Source {s!r} on {r['Effective Date']} is not in data/tariffs.csv")
            if tariffs[s]["Effective Date"] != r["Effective Date"]:
                sys.exit(f"{name}: row dated {r['Effective Date']} cites Supplement {s}, "
                         f"which is effective {tariffs[s]['Effective Date']}")
    return missing


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


def rider_values(riders, target_date):
    values = {}
    for name in RIDERS:
        row = as_of(riders, target_date, Rider=name)
        if row is None:
            return None
        values[name] = row["Value"]
    return values


def distribution_total(dist, riders, target_date, cls, season):
    base_row = as_of(dist, target_date, Class=cls, Season=season)
    r = rider_values(riders, target_date)
    if base_row is None or r is None:
        return None

    # 1. Base distribution energy charge plus per-kWh riders
    subtotal = base_row["Base Rate"] + r["Rider 5"] + r["Rider 15A"]

    # 2. DSIC (Rider 22) applies to the distribution subtotal (stored as 2.17, not 0.0217)
    with_dsic = subtotal * (1 + r["Rider 22"] / 100)

    # 3. STAS (Rider 10) applies on top, including to the DSIC
    return with_dsic * (1 + r["Rider 10"] / 100)


def _num(v, unit):
    s = f"{v:g}".replace("-", "−")
    return s + ("%" if unit == "%" else "¢")


def changes_for(tables, cls, dt):
    """What changed on dt for this class, with the supplement behind each
    change. Returns a list of dicts: kind (common/flat/tou), label, detail,
    source, url. Components appearing for the first time are not listed."""
    tariffs = tables["tariffs"]
    before = dt - timedelta(days=1)
    seasonal = is_seasonal(tables["dist"], cls)
    season = get_season(dt) if seasonal else "All"
    out = []

    def add(kind, label, detail, src):
        out.append({"kind": kind, "label": label, "detail": detail, "source": src or None,
                    "url": tariffs.get(src, {}).get("URL") or None})

    if seasonal and get_season(before) != season:
        add("common", f"{season} rates begin", "", None)

    for r in tables["dist"]:
        if r["Effective Date"] == dt and r["Class"] == cls and r["Season"] == season:
            prev = as_of(tables["dist"], before, Class=cls, Season=season)
            if prev:
                add("common", "Base distribution rate",
                    f"{_num(prev['Base Rate'], '¢')} → {_num(r['Base Rate'], '¢')}", r["Source"])

    for r in tables["riders"]:
        if r["Effective Date"] == dt:
            prev = as_of(tables["riders"], before, Rider=r["Rider"])
            if prev:
                unit = RIDERS[r["Rider"]]
                add("common", RIDER_LABELS[r["Rider"]],
                    f"{_num(prev['Value'], unit)} → {_num(r['Value'], unit)}", r["Source"])

    for r in tables["trans"]:
        if r["Effective Date"] == dt and r["Class"] == cls:
            prev = as_of(tables["trans"], before, Class=cls)
            if prev:
                add("common", "Transmission",
                    f"{_num(prev['Transmission'], '¢')} → {_num(r['Transmission'], '¢')}", r["Source"])

    for r in tables["supply"]:
        if r["Effective Date"] == dt:
            prev = as_of(tables["supply"], before)
            if prev:
                add("flat", "Supply", f"{_num(prev['Rate'], '¢')} → {_num(r['Rate'], '¢')}", r["Source"])

    tou_today = [r for r in tables["supply_tou"] if r["Effective Date"] == dt]
    if tou_today:
        prev = as_of(tables["supply_tou"], before, Period="Peak")
        peak = next((r for r in tou_today if r["Period"] == "Peak"), None)
        if prev and peak:
            add("tou", "Time-of-Use supply",
                f"Peak {_num(prev['Rate'], '¢')} → {_num(peak['Rate'], '¢')}", peak["Source"])

    return out


def calculation_inputs(tables, cls, dt):
    """Every input to the rate on dt, with the supplement it comes from, so
    the page can show the full calculation."""
    tariffs = tables["tariffs"]
    seasonal = is_seasonal(tables["dist"], cls)
    season = get_season(dt) if seasonal else "All"

    def item(row, value, label, unit="¢"):
        src = row["Source"] or None
        return {"label": label, "value": value, "unit": unit,
                "source": src, "url": tariffs.get(src, {}).get("URL")}

    base = as_of(tables["dist"], dt, Class=cls, Season=season)
    base_label = f"Base energy charge (Rate {cls}" + (f", {season.lower()})" if seasonal else ")")
    out = {
        "season": season,
        "base": item(base, base["Base Rate"], base_label),
        "riders": {},
        "tou": {},
    }
    for name, unit in RIDERS.items():
        row = as_of(tables["riders"], dt, Rider=name)
        out["riders"][name] = item(row, row["Value"], RIDER_LABELS[name], unit)
    supply = as_of(tables["supply"], dt)
    out["supply"] = item(supply, supply["Rate"], "Supply (Rider 8)")
    trans = as_of(tables["trans"], dt, Class=cls)
    out["trans"] = item(trans, trans["Transmission"], "Transmission (Appendix A)")
    for period in TOU_PERIODS:
        row = as_of(tables["supply_tou"], dt, Period=period)
        if row:
            out["tou"][period] = item(row, row["Rate"], f"{period} supply (Rider 8)")
    return out


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

    # TOU rates, same shape plus a Period column.
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
    missing = validate_sources(load_all())
    if missing:
        print(f"Note: {missing} source rows have no Source supplement recorded yet")
    flat_rows, tou_rows = build_tables(date.today())
    write_output(flat_rows, tou_rows)
    print(f"Wrote {OUTPUT / 'rates.csv'} ({len(flat_rows)} rows)")
    print(f"Wrote {OUTPUT / 'rates_tou.csv'} ({len(tou_rows)} rows)")
