#!/usr/bin/env python

import csv
import os
from datetime import datetime, timedelta
from decimal import Decimal

DATA_DIR = "data"
OUTPUT_DIR = "output"

DISTRIBUTION_FILE = os.path.join(DATA_DIR, "distribution.csv")
SUPPLY_FILE = os.path.join(DATA_DIR, "supply.csv")
SUPPLY_TOU_FILE = os.path.join(DATA_DIR, "supply_tou.csv")

RATES_CSV = os.path.join(OUTPUT_DIR, "rates.csv")
RATES_TOU_CSV = os.path.join(OUTPUT_DIR, "rates_tou.csv")
LOOKAHEAD_DAYS = 60

# --- Read distribution ---
def read_distribution(path):
    records = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eff_date = datetime.strptime(row["Effective Date"], "%Y-%m-%d").date()
            base = Decimal(row["Base Rate"])
            rider5 = Decimal(row["Rider 5"])
            rider15a = Decimal(row["Rider 15a"])
            rider10 = Decimal(row["Rider 10 (%)"])
            dist_rate = (base + rider5 + rider15a) * (1 + rider10 / 100)
            records.append({
                "Effective Date": eff_date,
                "Class": row["Class"],
                "Season": row["Season"],
                "Distribution Rate": dist_rate
            })
    return records

# --- Read flat supply ---
def read_supply_flat(path):
    records = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eff_date = datetime.strptime(row["Effective Date"], "%m/%d/%Y").date()
            rate = Decimal(row["Rate"])
            transmission = Decimal(row["Transmission"])
            cls = row["Class"]
            if cls in ("RH", "RA"):
                for season in ("Summer", "Winter"):
                    records.append({
                        "Effective Date": eff_date,
                        "Class": cls,
                        "Season": season,
                        "Supply Rate": rate,
                        "Transmission Rate": transmission
                    })
            else:  # RS
                records.append({
                    "Effective Date": eff_date,
                    "Class": cls,
                    "Season": "All",
                    "Supply Rate": rate,
                    "Transmission Rate": transmission
                })
    return records

# --- Read TOU supply ---
def read_supply_tou(path):
    records = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eff_date = datetime.strptime(row["Effective Date"], "%m/%d/%Y").date()
            rate = Decimal(row["Rate"])
            transmission = Decimal(row["Transmission"])
            cls = row["Class"]
            period = row["Period"]
            if cls in ("RH", "RA"):
                for season in ("Summer", "Winter"):
                    records.append({
                        "Effective Date": eff_date,
                        "Class": cls,
                        "Season": season,
                        "Period": period,
                        "Supply Rate": rate,
                        "Transmission Rate": transmission
                    })
            else:  # RS
                records.append({
                    "Effective Date": eff_date,
                    "Class": cls,
                    "Season": "All",
                    "Period": period,
                    "Supply Rate": rate,
                    "Transmission Rate": transmission
                })
    return records

# --- Determine season by date ---
def get_season(date):
    month = date.month
    return "Summer" if 5 <= month <= 10 else "Winter"

# --- Generate seasonal boundary dates ---
def add_season_boundaries(dist_records, supply_records):
    years = set(r["Effective Date"].year for r in dist_records + supply_records)
    boundaries = []
    for y in years:
        boundaries.append(datetime(y, 5, 1).date())   # Summer start
        boundaries.append(datetime(y, 11, 1).date())  # Winter start
    return boundaries

# --- Build timeline ---
def build_timeline(dist_records, supply_records, tou=False):
    results = []

    # Calculate Cutoff Date
    today = datetime.now().date()
    cutoff_date = today + timedelta(days=LOOKAHEAD_DAYS)

    if tou:
        classes = set((r["Class"], r["Season"], r["Period"]) for r in supply_records)
    else:
        classes = set((r["Class"], r["Season"]) for r in dist_records) | \
                  set((r["Class"], r["Season"]) for r in supply_records)

    for key in classes:
        if tou:
            cls, season, period = key
            dlist = [r for r in dist_records if r["Class"] == cls and r["Season"] == season]
            slist = [r for r in supply_records if r["Class"] == cls and r["Season"] == season and r.get("Period") == period]
        else:
            cls, season = key
            dlist = [r for r in dist_records if r["Class"] == cls and r["Season"] == season]
            slist = [r for r in supply_records if r["Class"] == cls and r["Season"] == season]

        if not dlist or not slist:
            continue

        # RS: only use actual rate change dates
        # RA/RH: include seasonal boundaries
        if cls in ("RH", "RA"):
            dates = sorted(set([r["Effective Date"] for r in dlist] +
                               [r["Effective Date"] for r in slist] +
                               add_season_boundaries(dlist, slist)))
        else:  # RS
            dates = sorted(set([r["Effective Date"] for r in dlist] +
                               [r["Effective Date"] for r in slist]))

        for date_item in dates:
            # Skip dates that are too far in the future
            if date_item > cutoff_date:
                continue

            current_season = get_season(date_item)

            # RA/RH only print row if season matches
            if cls in ("RH", "RA") and season != current_season:
                continue
            # RS always print any rate change (season ignored)

            d_candidates = [r for r in dlist if r["Effective Date"] <= date_item]
            s_candidates = [r for r in slist if r["Effective Date"] <= date_item]
            if not d_candidates or not s_candidates:
                continue

            drow = max(d_candidates, key=lambda r: r["Effective Date"])
            srow = max(s_candidates, key=lambda r: r["Effective Date"])
            dist_rate = drow["Distribution Rate"]
            supply_rate = srow["Supply Rate"]
            transmission_rate = srow["Transmission Rate"]
            total_rate = dist_rate + supply_rate + transmission_rate

            out = {
                "Effective Date": date_item.isoformat(),
                "Class": cls,
                "Season": current_season if cls in ("RH", "RA") else season,
                "Distribution Rate": round(dist_rate, 4),
                "Supply Rate": round(supply_rate, 4),
                "Transmission Rate": round(transmission_rate, 4),
                "Total Rate": round(total_rate, 4),
            }
            if tou:
                out["Period"] = period
            results.append(out)

    sort_keys = ["Effective Date", "Class", "Season"] + (["Period"] if tou else [])
    results.sort(key=lambda r: tuple(r[k] for k in sort_keys))
    return results

# --- Main ---
def main():
    dist_records = read_distribution(DISTRIBUTION_FILE)

    # Flat supply rates
    supply_records = read_supply_flat(SUPPLY_FILE)
    combined = build_timeline(dist_records, supply_records, tou=False)
    with open(RATES_CSV, "w", newline="") as f:
        fieldnames = ["Effective Date", "Class", "Season", "Distribution Rate", "Supply Rate", "Transmission Rate", "Total Rate"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined)

    # TOU supply rates
    supply_tou_records = read_supply_tou(SUPPLY_TOU_FILE)
    combined_tou = build_timeline(dist_records, supply_tou_records, tou=True)
    with open(RATES_TOU_CSV, "w", newline="") as f:
        fieldnames = ["Effective Date", "Class", "Season", "Period", "Distribution Rate", "Supply Rate", "Transmission Rate", "Total Rate"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined_tou)

if __name__ == "__main__":
    main()
