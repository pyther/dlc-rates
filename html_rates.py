import csv
import json
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

            # Calculate PTC and round to 4 decimal places to avoid floating point issues
            supply = float(row["Supply Rate"])
            transmission = float(row["Transmission Rate"])
            ptc = round(supply + transmission, 4)

            rate_data = {
                "date": row["Effective Date"],
                "season": row["Season"],
                "distribution_rate": float(row["Distribution Rate"]),
                "ptc_rate": ptc,
                "total_rate": float(row["Total Rate"]),
            }

            if tou:
                rate_data["period"] = row["Period"]

            rates[cls].append(rate_data)

    # Sort newest to oldest
    for cls_rates in rates.values():
        cls_rates.sort(key=lambda r: r['date'], reverse=True)
    return rates

def generate_html(flat_rates, tou_rates):
    classes = ["RS", "RH", "RA"]
    rate_definitions = {
        "RS": "RS (Residential Service)",
        "RA": "RA (Residential Add-On Heat Pump)",
        "RH": "RH (Residential Heating)"
    }

    # Serialize flat rates to JSON to pass to Chart.js
    rates_json_str = json.dumps(flat_rates)

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Duquesne Light Company Electric Rates</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body { font-family: Arial, sans-serif; padding: 20px; line-height: 1.5; }
h1 { margin-bottom: 10px; }
h2 { margin-top: 30px; margin-bottom: 15px; }
.tab { cursor: pointer; padding: 10px 20px; border: 1px solid #ccc; display: inline-block; margin-right: 5px; border-radius: 4px; background-color: #f9f9f9; font-weight: bold; }
.tab.active { background-color: #e6e6e6; border-bottom: 2px solid #333; }
.section { display: none; margin-top: 20px; }
.section.active { display: block; }

/* Sub-tab Toggle Styling */
.rate-type-toggle { margin-bottom: 20px; display: inline-flex; border-radius: 5px; overflow: hidden; border: 1px solid #0066cc; }
.toggle-btn { padding: 8px 16px; cursor: pointer; border: none; background: white; color: #0066cc; font-size: 0.95em; font-weight: bold; margin: 0; outline: none; }
.toggle-btn:not(:last-child) { border-right: 1px solid #0066cc; }
.toggle-btn.active { background: #0066cc; color: white; }
.rate-container { display: none; }
.rate-container.active { display: block; }

/* Chart Container */
.chart-container { position: relative; height: 350px; width: 100%; max-width: 800px; margin-bottom: 30px; }

table { border-collapse: collapse; width: 100%; max-width: 800px; }
th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; font-size: 0.95em; }
th { background-color: #f2f2f2; color: #333; }
.num { text-align: right; }
.group-start td { border-top: 2px solid #999; }
.date-cell { color: #555; }
a { color: #0066cc; text-decoration: none; }
a:hover { text-decoration: underline; }
.info { background-color: #ffffe0; padding: 15px; border-left: 5px solid #ffcc00; margin-bottom: 20px; max-width: 1000px; }
.info details { background-color: #f9f9f9; padding: 10px; margin-bottom: 10px; }
.extra-row { display: none; }
.show-more-btn { margin: 5px 0 15px 0; padding: 5px 10px; cursor: pointer; }
</style>
</head>
<body>
<h1>Duquesne Light Company Electric Rates</h1>

<div class="info">
  <p>This page provides a <strong>best-effort estimate</strong> of <a href="https://duquesnelight.com" target="_blank" rel="noopener noreferrer">Duquesne Light Company (DLC)</a> residential electricity rates, shown in <strong>&cent;/kWh</strong>.</p>

  <p>This is an independent project. The calculations require carefully reviewing the DLC tariff and making informed assumptions. It is intended for informational purposes only and <strong>may not match actual bills</strong> perfectly. DLC’s official billing is always the authoritative source.</p>

  <details>
    <summary><strong>How are these columns calculated?</strong></summary>
    <p>The rates displayed are broken down as follows:</p>
    <ul>
      <li><strong>Total Rate:</strong> The bottom-line price per kWh (PTC + Distribution).</li>
      <li><strong>Price to Compare (PTC):</strong> The cost of the actual electricity generation and transmission. In the raw tariff, this consists of two separate charges (Supply + Transmission), which are combined here. <br><br><em>A note on third-party suppliers:</em> While Pennsylvania allows consumers to choose an alternative supplier for this portion of the bill, extreme caution is recommended. Many third-party offers use temporary "teaser rates" that later transition into expensive variable rates, or include hidden monthly fees. The PTC shown here is the baseline default rate, which can be used to verify if an alternative offer provides genuine savings.</li>
      <li><strong>Distribution:</strong> The cost to deliver power to a residence (poles, wires, infrastructure). This is paid to DLC regardless of who supplies the electricity. Because DLC does not publish a single consolidated "distribution rate," this figure is calculated by combining the base rate with the following riders:
        <ul>
          <li><strong>Rider No. 5</strong> &ndash; Universal Service Charge</li>
          <li><strong>Rider No. 10</strong> &ndash; State Tax Adjustment</li>
          <li><strong>Rider No. 15A</strong> &ndash; Phase IV Energy Efficiency and Conservation Surcharge</li>
        </ul>
      </li>
    </ul>
  </details>

  <details>
    <summary><strong>A Note on the Financial Risk of Time-of-Use (TOU) Rates</strong></summary>
    <p>While TOU plans are marketed as a way to save money, the risk-to-reward ratio rarely favors the consumer. The "Peak" rate penalty is so severe compared to the standard flat rate that the margins for actually saving money are incredibly thin.</p>
    <p>Even for households with Electric Vehicles (EVs) that aggressively shift usage to overnight hours, the savings are often marginal at best. Because the peak rate is so expensive, a single mistake—such as accidentally charging a vehicle, running the AC, or doing laundry during a peak window—can instantly wipe out weeks of careful energy management. Consumers should strictly evaluate their ability to avoid peak-hour usage with zero margin for error before opting into these rates.</p>
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
        flat_colspan = 4
        tou_colspan = 5

        html += f'<div class="section" id="section-{cls}">\n'
        html += f"<h2>{rate_definitions[cls]}</h2>\n"

        # --- Toggle Buttons ---
        html += f"""
        <div class="rate-type-toggle">
            <button class="toggle-btn active" onclick="switchRateType(event, '{cls}', 'flat')">Flat Rates</button>
            <button class="toggle-btn" onclick="switchRateType(event, '{cls}', 'tou')">Time-of-Use Rates</button>
        </div>
        """

        # --- Flat rates Container ---
        html += f'<div id="{cls}-flat" class="rate-container active">\n'

        # Chart.js Canvas
        html += f'<div class="chart-container"><canvas id="chart-{cls}"></canvas></div>\n'

        html += f"<table>\n<tr><th>Effective Date</th><th class='num'>Total (&cent;/kWh)</th><th class='num'>Price to Compare (&cent;/kWh)</th><th class='num'>Distribution (&cent;/kWh)</th></tr>\n"
        for i, r in enumerate(flat_rates.get(cls, [])):
            row_class = "extra-row" if i >= MAX_ROWS else ""
            display_date = f"{r['date']} ({r['season']})" if cls in ("RA", "RH") else r['date']
            html += f"<tr class='{row_class}'><td>{display_date}</td><td class='num'>{r['total_rate']}</td><td class='num'>{r['ptc_rate']}</td><td class='num'>{r['distribution_rate']}</td></tr>\n"

        if len(flat_rates.get(cls, [])) > MAX_ROWS:
            html += f"<tr><td colspan='{flat_colspan}'><button class='show-more-btn' onclick='showMore(this)'>Show More</button></td></tr>\n"
        html += "</table>\n</div>\n"

        # --- TOU rates Container ---
        html += f'<div id="{cls}-tou" class="rate-container">\n'
        html += f"<table>\n<tr><th>Effective Date</th><th>Period</th><th class='num'>Total (&cent;/kWh)</th><th class='num'>Price to Compare (&cent;/kWh)</th><th class='num'>Distribution (&cent;/kWh)</th></tr>\n"

        last_date = None

        for i, r in enumerate(tou_rates.get(cls, [])):
            is_new_group = False
            if r['date'] != last_date:
                last_date = r['date']
                is_new_group = True

            # Apply a top border if it's a new group (but skip the very first row)
            classes_list = []
            if is_new_group and i > 0:
                classes_list.append("group-start")
            if i >= MAX_ROWS:
                classes_list.append("extra-row")

            row_class = " ".join(classes_list)
            class_attr = f" class='{row_class}'" if row_class else ""

            # Only print the date if it is the first row of a new group
            display_date = ""
            if is_new_group:
                display_date = f"{r['date']} ({r['season']})" if cls in ("RA", "RH") else r['date']

            html += f"<tr{class_attr}><td class='date-cell'><strong>{display_date}</strong></td><td>{r['period']}</td><td class='num'>{r['total_rate']}</td><td class='num'>{r['ptc_rate']}</td><td class='num'>{r['distribution_rate']}</td></tr>\n"

        if len(tou_rates.get(cls, [])) > MAX_ROWS:
            html += f"<tr><td colspan='{tou_colspan}'><button class='show-more-btn' onclick='showMore(this)'>Show More</button></td></tr>\n"

        html += "</table>\n</div>\n"
        html += "</div>\n"

    # Tabs, Toggles, Chart Logic, and Show More script
    html += f"""
<script>
// --- Chart.js Integration ---
const flatRatesData = {rates_json_str};

function initCharts() {{
    const classes = ['RS', 'RH', 'RA'];

    classes.forEach(cls => {{
        const ctx = document.getElementById('chart-' + cls);
        if (!ctx) return;

        const data = flatRatesData[cls] || [];

        // Data is currently newest to oldest. Reverse it for chronological charting.
        const chartData = [...data].reverse();

        // For RH and RA, append the season to the date for the chart tooltip
        const labels = chartData.map(d => (cls === 'RH' || cls === 'RA') ? d.date + ' (' + d.season + ')' : d.date);
        const totalRates = chartData.map(d => d.total_rate);
        const ptcRates = chartData.map(d => d.ptc_rate);
        const distRates = chartData.map(d => d.distribution_rate);

        new Chart(ctx, {{
            data: {{
                labels: labels,
                datasets: [
                    {{
                        type: 'line',
                        label: 'Total Rate Trend',
                        data: totalRates,
                        borderColor: '#1e293b', /* Crisp Dark Slate */
                        backgroundColor: '#1e293b',
                        borderWidth: 3,
                        pointRadius: 4,
                        fill: false, /* No background fill */
                        tension: 0.2
                    }},
                    {{
                        type: 'bar',
                        label: 'Price to Compare (PTC)',
                        data: ptcRates,
                        backgroundColor: 'rgba(245, 158, 11, 0.8)', /* Warm Amber */
                        borderColor: '#d97706',
                        borderWidth: 1,
                        stack: 'Stack 0',
                        barPercentage: 0.5 /* Slims down the bar width */
                    }},
                    {{
                        type: 'bar',
                        label: 'Distribution',
                        data: distRates,
                        backgroundColor: 'rgba(59, 130, 246, 0.8)', /* Utility Blue */
                        borderColor: '#2563eb',
                        borderWidth: 1,
                        stack: 'Stack 0',
                        barPercentage: 0.5 /* Slims down the bar width */
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{
                    mode: 'index',
                    intersect: false,
                }},
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }},
                scales: {{
                    x: {{
                        stacked: true, /* Enable bar stacking horizontally */
                        ticks: {{
                            maxTicksLimit: 12
                        }}
                    }},
                    y: {{
                        stacked: true, /* Enable bar stacking vertically */
                        beginAtZero: true,
                        title: {{ display: true, text: 'Cents per kWh (¢)' }}
                    }}
                }}
            }}
        }});
    }});
}}

// Initialize charts after script loads
window.addEventListener('DOMContentLoaded', initCharts);

// --- UI Interaction Logic ---
// Main Class Tabs
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

// Sub-Tabs for Flat vs TOU
function switchRateType(event, cls, type) {{
    const section = document.getElementById('section-' + cls);

    // Update button states
    section.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');

    // Update container visibility
    section.querySelectorAll('.rate-container').forEach(c => c.classList.remove('active'));
    document.getElementById(cls + '-' + type).classList.add('active');
}}

function showMore(btn){{
    const table = btn.closest('table');
    table.querySelectorAll('.extra-row').forEach(r => r.style.display = 'table-row');
    btn.style.display = 'none';
}}
</script>
<footer style="margin-top: 40px; font-size: 0.85em; color: #555;">
  <p>
    This website is an independent project and is not affiliated with or endorsed by
    <a href="https://www.duquesnelight.com" target="_blank" rel="noopener noreferrer">Duquesne Light Company (DLC)</a>.
    All data is provided "as is" for informational purposes only and represents a best-effort estimate of residential electricity rates.
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
