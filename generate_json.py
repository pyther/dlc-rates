import csv
import json
import os
from collections import defaultdict
from datetime import datetime, date

OUTPUT_DIR = "output"

RATES_CSV = os.path.join(OUTPUT_DIR, "rates.csv")
RATES_TOU_CSV = os.path.join(OUTPUT_DIR, "rates_tou.csv")
RATES_JSON = os.path.join(OUTPUT_DIR, "rates.json")

def read_csv(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col in ["Distribution Rate", "Supply Rate", "Total Rate"]:
                row[col] = float(row[col])
            rows.append(row)
    return rows

def generate_json(flat_csv=RATES_CSV, tou_csv=RATES_TOU_CSV, output_file=RATES_JSON):
    flat_rates = read_csv(flat_csv)
    tou_rates = read_csv(tou_csv)
    data = defaultdict(lambda: {"current": {}, "history": [], "tou_history": []})
    today = date.today()

    # --- Flat rates ---
    for row in flat_rates:
        cls = row["Class"]
        data[cls]["history"].append(row)

    for cls in data:
        # RS flat all year: ignore season in current
        if cls == "RS":
            past_rates = [r for r in data[cls]["history"] if datetime.fromisoformat(r["Effective Date"]).date() <= today]
            latest = max(past_rates, key=lambda r: datetime.fromisoformat(r["Effective Date"])) if past_rates else \
                     min(data[cls]["history"], key=lambda r: datetime.fromisoformat(r["Effective Date"]))
            data[cls]["current"]["flat"] = latest
        else:  # RA/RH seasonal
            past_rates = [r for r in data[cls]["history"] if datetime.fromisoformat(r["Effective Date"]).date() <= today]
            latest = max(past_rates, key=lambda r: datetime.fromisoformat(r["Effective Date"])) if past_rates else \
                     min(data[cls]["history"], key=lambda r: datetime.fromisoformat(r["Effective Date"]))
            data[cls]["current"]["flat"] = latest

    # --- TOU rates ---
    for row in tou_rates:
        cls = row["Class"]
        data[cls]["tou_history"].append(row)

    for cls in data:
        past_tou = [r for r in data[cls]["tou_history"] if datetime.fromisoformat(r["Effective Date"]).date() <= today]
        latest_tou = max(past_tou, key=lambda r: datetime.fromisoformat(r["Effective Date"])) if past_tou else \
                     min(data[cls]["tou_history"], key=lambda r: datetime.fromisoformat(r["Effective Date"]))

        # For RS, we ignore Season in TOU current
        period_rates = {r["Period"]: r["Total Rate"] for r in tou_rates
                        if r["Class"] == cls and r["Effective Date"] == latest_tou["Effective Date"] and
                        (cls != "RS" and r["Season"] == latest_tou["Season"] or cls == "RS")}

        current_tou = {"Season": latest_tou["Season"]} if cls != "RS" else {}
        current_tou.update(period_rates)
        data[cls]["current"]["tou"] = current_tou

    # Sort history oldest → newest
    for cls in data:
        data[cls]["history"].sort(key=lambda r: datetime.fromisoformat(r["Effective Date"]))
        data[cls]["tou_history"].sort(key=lambda r: datetime.fromisoformat(r["Effective Date"]))

    # Write JSON
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"JSON file written to {output_file}")

if __name__ == "__main__":
    generate_json()

