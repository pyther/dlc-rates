import csv
from pathlib import Path

# Input files
RATES_CSV = "output/rates.csv"
RATES_TOU_CSV = "output/rates_tou.csv"
OUTPUT_HTML = "docs/index.html"
MAX_ROWS = 20  # rows to show initially

# --- Read CSV ---
def read_csv(file_path, tou=False):
    rates = {}
    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = row["Class"]
            if cls not in rates:
                rates[cls] = []
            if tou:
                rates[cls].append({
                    "date": row["Effective Date"],
                    "season": row["Season"],
                    "period": row["Period"],
                    "distribution_rate": float(row["Distribution Rate"]),
                    "supply_rate": float(row["Supply Rate"]),
                    "transmission_rate": float(row["Transmission Rate"]),
                    "total_rate": float(row["Total Rate"]),
                })
            else:
                rates[cls].append({
                    "date": row["Effective Date"],
                    "season": row["Season"],
                    "distribution_rate": float(row["Distribution Rate"]),
                    "supply_rate": float(row["Supply Rate"]),
                    "transmission_rate": float(row["Transmission Rate"]),
                    "total_rate": float(row["Total Rate"]),
                })
    # Sort newest to oldest
    for cls_rates in rates.values():
        cls_rates.sort(key=lambda r: r['date'], reverse=True)
    return rates

def generate_html(flat_rates, tou_rates):
    classes = ["RS", "RH", "RA"]
    rate_definitions = {
        "RS": "Residential Service",
        "RA": "Residential Service Add-On Heat Pump",
        "RH": "Residential Service Heating"
    }

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Duquesne Light Company Electric Rates</title>
<style>
body { font-family: Arial, sans-serif; padding: 20px; line-height: 1.5; }
h1 { margin-bottom: 10px; }
h2 { margin-top: 30px; }
.tab { cursor: pointer; padding: 10px 20px; border: 1px solid #ccc; display: inline-block; margin-right: 5px; border-radius: 4px; background-color: #f9f9f9; }
.tab.active { background-color: #e6e6e6; }
.section { display: none; margin-top: 20px; }
.section.active { display: block; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; }
th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; font-size: 0.95em; }
th { background-color: #f2f2f2; color: #333; }
a { color: #0066cc; text-decoration: none; }
a:hover { text-decoration: underline; }
.info { background-color: #ffffe0; padding: 15px; border-left: 5px solid #ffcc00; margin-bottom: 20px; }
.info details { background-color: #f9f9f9; padding: 10px; margin-bottom: 10px; }
.tou-alt { background-color: #e8e8e8; }
.extra-row { display: none; }
.show-more-btn { margin: 5px 0 15px 0; padding: 5px 10px; cursor: pointer; }
</style>
</head>
<body>
<h1>Duquesne Light Company Electric Rates</h1>

<div class="info">
  <p>This page provides a <strong>best-effort estimate</strong> of <a href="https://duquesnelight.com" target="_blank" rel="noopener noreferrer">Duquesne Light Company (DLC)</a> residential electricity rates, shown in <strong>&cent;/kWh</strong>.</p>

  <p>Distribution rates are <em>not officially published</em>; the calculation requires carefully reading the DLC tariff and making informed assumptions about what should be included. This page is intended for informational purposes only and <strong>may not match your actual bill</strong>. DLC’s billing and rates are the authoritative source.</p>

  <details>
    <summary><strong>Calculation Notes</strong></summary>
    <p><strong>Distribution rates</strong> are derived from the DLC tariff for RS, RA, and RH classes and include:</p>
    <ul>
      <li><strong>Rider No. 5</strong> – Universal Service Charge</li>
      <li><strong>Rider No. 10</strong> – State Tax Adjustment</li>
      <li><strong>Rider No. 15A</strong> – Phase IV Energy Efficiency and Conservation Surcharge</li>
    </ul>
    <p><strong>Supply and Transmission rates</strong> are taken directly from the DLC tariff. DLC publishes a “Price to Compare” (PTC), which is simply the sum of Supply + Transmission. Because those values are already shown separately here, PTC is not displayed as its own column.</p>
  </details>

  <details>
    <summary><strong>Resources</strong></summary>
    <ul>
      <li><a href="https://duquesnelight.com/service-reliability/service-map/rates/tariff-resources" target="_blank">DLC Tariff Resources</a></li>
      <li><a href="https://duquesnelight.com/service-reliability/service-map/rates/residential-rates" target="_blank">Residential Rates</a></li>
      <li><a href="https://duquesnelight.com/energy-money-savings/electric-vehicles/charge-smart-and-save/time-of-use-supply-rate" target="_blank">Time-of-Use Supply Rates</a></li>
    </ul>
  </details>
</div>

<div id="tabs">
"""
    # Tab buttons
    for cls in classes:
        html += f'<div class="tab" data-class="{cls}">{rate_definitions[cls]}</div>\n'
    html += '</div>\n'

    # Sections per class
    for cls in classes:
        html += f'<div class="section" id="section-{cls}">\n'
        # Flat rates
        html += f"<h2>Flat Rates ({rate_definitions[cls]})</h2>\n"
        html += f"<table>\n<tr><th>Effective Date</th><th>Season</th><th>Distribution (&cent;/kWh)</th><th>Supply (&cent;/kWh)</th><th>Transmission (&cent;/kWh)</th><th>Total (&cent;/kWh)</th></tr>\n"
        for i, r in enumerate(flat_rates.get(cls, [])):
            row_class = "extra-row" if i >= MAX_ROWS else ""
            html += f"<tr class='{row_class}'><td>{r['date']}</td><td>{r['season']}</td><td>{r['distribution_rate']}</td><td>{r['supply_rate']}</td><td>{r['transmission_rate']}</td><td>{r['total_rate']}</td></tr>\n"
        if len(flat_rates.get(cls, [])) > MAX_ROWS:
            html += "<tr><td colspan='5'><button class='show-more-btn' onclick='showMore(this)'>Show More</button></td></tr>\n"
        html += "</table>\n"

        # TOU rates
        html += f"<h2>Time-of-Use Rates ({rate_definitions[cls]})</h2>\n"
        html += f"<table>\n<tr><th>Effective Date</th><th>Season</th><th>Period</th><th>Distribution (&cent;/kWh)</th><th>Supply (&cent;/kWh)</th><th>Transmission (&cent;/kWh)</th><th>Total (&cent;/kWh)</th></tr>\n"

        if cls in ("RA", "RH"):
            last_date = None
            alt = False
            first_group = True
            for i, r in enumerate(tou_rates.get(cls, [])):
                if r['date'] != last_date:
                    last_date = r['date']
                    if first_group:
                        alt = False
                        first_group = False
                    else:
                        alt = not alt
                row_class = "tou-alt"
                if i >= MAX_ROWS:
                    row_class += " extra-row"
                if not alt:
                    row_class = row_class.replace("tou-alt","")
                html += f"<tr class='{row_class}'><td>{r['date']}</td><td>{r['season']}</td><td>{r['period']}</td><td>{r['distribution_rate']}</td><td>{r['supply_rate']}</td><td>{r['transmission_rate']}</td><td>{r['total_rate']}</td></tr>\n"
        else:
            for i, r in enumerate(tou_rates.get(cls, [])):
                row_class = "extra-row" if i >= MAX_ROWS else ""
                html += f"<tr class='{row_class}'><td>{r['date']}</td><td>{r['season']}</td><td>{r['period']}</td><td>{r['distribution_rate']}</td><td>{r['supply_rate']}</td><td>{r['transmission_rate']}</td><td>{r['total_rate']}</td></tr>\n"

        if len(tou_rates.get(cls, [])) > MAX_ROWS:
            html += "<tr><td colspan='6'><button class='show-more-btn' onclick='showMore(this)'>Show More</button></td></tr>\n"

        html += "</table>\n"
        html += "</div>\n"

    # Tabs and Show More script
    html += f"""
<script>
const tabs = document.querySelectorAll('.tab');
const sections = document.querySelectorAll('.section');

tabs.forEach(tab => {{
    tab.addEventListener('click', () => {{
        tabs.forEach(t => t.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('section-' + tab.dataset.class).classList.add('active');
    }});
}});
tabs[0].click();

function showMore(btn){{
    const table = btn.closest('table');
    table.querySelectorAll('.extra-row').forEach(r => r.style.display = 'table-row');
    btn.style.display = 'none';
}}
</script>
<footer style="margin-top: 40px; font-size: 0.85em; color: #555;">
  <p>
    &copy; 2025 Matthew Gyurgyik. This website is an independent project and is not affiliated with or endorsed by
    <a href="https://www.duquesnelight.com" target="_blank" rel="noopener noreferrer">Duquesne Light Company (DLC)</a>.
    All data is provided for informational purposes only and represents a best-effort estimate of residential electricity rates.
    Official rates, billing, and tariffs from DLC are the authoritative source.
    For questions regarding your bill or service, please contact DLC directly.
  </p>
  <p>
    GitHub Project: <a href="https://github.com/pyther/dlc-rates" target="_blank" rel="noopener noreferrer">https://github.com/pyther/dlc-rates</a>
  </p>
</footer>

</body>
</html>
"""
    return html

def main():
    flat_rates = read_csv(RATES_CSV)
    tou_rates = read_csv(RATES_TOU_CSV, tou=True)

    html = generate_html(flat_rates, tou_rates)
    Path(OUTPUT_HTML).write_text(html, encoding="utf-8")
    print(f"Static HTML generated at {OUTPUT_HTML}")

if __name__ == "__main__":
    main()
