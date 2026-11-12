#!/usr/bin/env python3
"""
html_rates.py — generate the static site at docs/index.html.

Rates are computed with csv_rates.build_tables() out to the latest filed
effective date in data/, so already-filed future changes (e.g. a supply
supplement effective next month) are included. The page itself decides,
using the viewer's current date, which row is "current" and which are
"scheduled" — so the site stays correct after a change date passes even
if it hasn't been rebuilt.
"""

import json
from datetime import date
from pathlib import Path

import csv_rates

OUTPUT_HTML = Path("docs/index.html")
TEMPLATE_DATA = "__RATE_DATA__"
TEMPLATE_BUILT = "__BUILT__"

CLASS_INFO = {
    "RS": {"name": "Residential Service", "short": "Standard"},
    "RH": {"name": "Residential Heating", "short": "Electric heat"},
    "RA": {"name": "Residential Add-On Heat Pump", "short": "Heat pump"},
}
PERIODS = ["Peak", "Off-Peak", "Super Off-Peak"]


def latest_filed_date(tables):
    """Latest effective date across every source file."""
    return max(r["Effective Date"]
               for name in ("riders", "dist", "trans", "supply", "supply_tou")
               for r in tables[name])


def build_payload():
    tables = csv_rates.load_all()
    csv_rates.validate_sources(tables)
    horizon = max(latest_filed_date(tables), date.today())
    flat_rows, tou_rows = csv_rates.build_tables(horizon)

    payload = {}
    for cls in csv_rates.CLASSES:
        payload[cls] = {**CLASS_INFO[cls], "seasonal": False, "flat": [], "tou": [], "changes": {}, "calc": {}}

    for dt, cls, season, dist, supply, trans, total in flat_rows:
        payload[cls]["flat"].append({
            "date": dt.isoformat(),
            "season": season,
            "total": round(total, 4),
            "ptc": round(supply + trans, 4),
            "supply": supply,
            "trans": trans,
            "dist": dist,
        })
        if season != "All":
            payload[cls]["seasonal"] = True

    tou_by_key = {}
    for dt, cls, season, period, dist, supply, trans, total in tou_rows:
        key = (cls, dt)
        if key not in tou_by_key:
            tou_by_key[key] = {"date": dt.isoformat(), "season": season, "dist": dist, "periods": {}}
            payload[cls]["tou"].append(tou_by_key[key])
        tou_by_key[key]["periods"][period] = {
            "total": round(total, 4),
            "ptc": round(supply + trans, 4),
        }

    # What changed on each date, and which tariff supplement changed it
    for cls, cls_data in payload.items():
        for iso in {r["date"] for r in cls_data["flat"] + cls_data["tou"]}:
            cls_data["changes"][iso] = csv_rates.changes_for(tables, cls, date.fromisoformat(iso))
            cls_data["calc"][iso] = csv_rates.calculation_inputs(tables, cls, date.fromisoformat(iso))

    # Newest first
    for cls_data in payload.values():
        cls_data["flat"].sort(key=lambda r: r["date"], reverse=True)
        cls_data["tou"].sort(key=lambda r: r["date"], reverse=True)

    return payload


def main():
    payload = build_payload()
    data_json = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.replace(TEMPLATE_DATA, data_json).replace(TEMPLATE_BUILT, date.today().isoformat())
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Static HTML generated at {OUTPUT_HTML}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unofficial DLC Rate Tracker</title>
<meta name="description" content="Current and historical Duquesne Light Company residential electricity rates in cents per kWh, including Price to Compare and Time-of-Use rates.">
<style>
:root {
  --bg: #f5f6f8;
  --surface: #ffffff;
  --surface-2: #f0f2f5;
  --text: #14181f;
  --muted: #5a6371;
  --border: #e1e4ea;
  --accent: #1d4ed8;
  --accent-soft: #e5ecfd;
  --ptc: #d97706;
  --dist: #2563eb;
  --peak: #dc2626;
  --offpeak: #d97706;
  --superoff: #059669;
  --up: #b91c1c;
  --down: #047857;
  --note-bg: #fff8e6;
  --note-border: #f2c94c;
  --shadow: 0 1px 2px rgba(16, 24, 40, .06), 0 1px 3px rgba(16, 24, 40, .08);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1216;
    --surface: #171b21;
    --surface-2: #1f242c;
    --text: #e8ebf0;
    --muted: #9aa3b0;
    --border: #2a303a;
    --accent: #7aa2ff;
    --accent-soft: #1c2740;
    --ptc: #f5a524;
    --dist: #6b9bff;
    --peak: #f87171;
    --offpeak: #f5a524;
    --superoff: #34d399;
    --up: #f87171;
    --down: #34d399;
    --note-bg: #2a2412;
    --note-border: #8a6d1a;
    --shadow: none;
  }
}
:root[data-theme="dark"] {
  --bg: #0f1216;
  --surface: #171b21;
  --surface-2: #1f242c;
  --text: #e8ebf0;
  --muted: #9aa3b0;
  --border: #2a303a;
  --accent: #7aa2ff;
  --accent-soft: #1c2740;
  --ptc: #f5a524;
  --dist: #6b9bff;
  --peak: #f87171;
  --offpeak: #f5a524;
  --superoff: #34d399;
  --up: #f87171;
  --down: #34d399;
  --note-bg: #2a2412;
  --note-border: #8a6d1a;
  --shadow: none;
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
a { color: var(--accent); }
.wrap { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }

header h1 { font-size: 1.6rem; margin: 0 0 4px; letter-spacing: -0.01em; }
header p { margin: 0; color: var(--muted); }
header .unofficial { margin-top: 8px; font-size: .88rem; }
header .unofficial strong { color: var(--text); }

.controls { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: flex-end; margin: 24px 0 16px; }
.control-label { display: block; font-size: .8rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 6px; }
.seg { display: inline-flex; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 3px; gap: 3px; flex-wrap: wrap; }
.seg button {
  font: inherit; border: 0; background: transparent; color: var(--text);
  padding: 7px 14px; border-radius: 7px; cursor: pointer; text-align: left; line-height: 1.25;
}
.seg button:hover { background: var(--surface); }
.seg button[aria-pressed="true"] { background: var(--surface); box-shadow: var(--shadow); outline: 1.5px solid var(--accent); }
.seg button .code { font-weight: 700; }
.seg button .sub { display: block; font-size: .78rem; color: var(--muted); }
.help-link { font-size: .9rem; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; box-shadow: var(--shadow); margin-bottom: 16px; }
.card h2 { font-size: 1.05rem; margin: 0 0 14px; }

/* Summary */
.summary { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr); gap: 24px; }
@media (max-width: 720px) { .summary { grid-template-columns: minmax(0, 1fr); gap: 18px; } }
.eyebrow { font-size: .85rem; color: var(--muted); margin: 0 0 2px; }
.big { font-size: 3rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.1; font-variant-numeric: tabular-nums; }
.big small { font-size: 1.1rem; font-weight: 500; color: var(--muted); margin-left: 4px; }
.meta { color: var(--muted); font-size: .9rem; margin-top: 6px; }
.delta { font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }
.delta.up { color: var(--up); }
.delta.down { color: var(--down); }
.delta.flat { color: var(--muted); }

.parts { display: flex; flex-direction: column; gap: 14px; }
.part-head { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
.part-name { font-weight: 600; }
.part-name .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 7px; vertical-align: baseline; }
.part-val { font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
.part-desc { color: var(--muted); font-size: .85rem; margin-top: 2px; }
.stackbar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; background: var(--surface-2); }
.stackbar span { display: block; height: 100%; }

.upcoming {
  margin-top: 18px; padding: 12px 14px; border-radius: 10px;
  background: var(--accent-soft); border: 1px solid var(--border); font-size: .95rem;
}
.upcoming strong { font-variant-numeric: tabular-nums; }

.tou-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
@media (max-width: 640px) { .tou-grid { grid-template-columns: minmax(0, 1fr); } }
.tou-card { border: 1px solid var(--border); border-radius: 12px; padding: 14px; border-top: 4px solid var(--c); }
.tou-card .name { font-weight: 600; }
.tou-card .val { font-size: 2rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; margin: 4px 0; }
.tou-card .val small { font-size: .9rem; font-weight: 500; color: var(--muted); }
.tou-card .cmp { font-size: .85rem; color: var(--muted); }

.estimator { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
.estimator label { font-weight: 600; }
.estimator input {
  font: inherit; width: 7em; padding: 6px 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--surface-2); color: var(--text);
}
.estimator .result { font-weight: 700; font-variant-numeric: tabular-nums; }
.estimator .fine { width: 100%; color: var(--muted); font-size: .8rem; }

/* Year-over-year comparison */
.compare-intro { color: var(--muted); font-size: .9rem; margin: -6px 0 12px; }
.compare-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.cmp-card { border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
.cmp-card .when { font-weight: 600; }
.cmp-card .when span { font-weight: 400; color: var(--muted); font-size: .85rem; }
.cmp-card .money-big { font-size: 1.8rem; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; margin: 6px 0 2px; }
.cmp-card .money-big.up { color: var(--up); }
.cmp-card .money-big.down { color: var(--down); }
.cmp-card .money-big small { font-size: .9rem; font-weight: 500; color: var(--muted); }
.cmp-card .detail { color: var(--muted); font-size: .85rem; font-variant-numeric: tabular-nums; }

/* Table */
.table-scroll { overflow-x: auto; margin: 0 -4px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 9px 10px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { font-size: .8rem; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .03em; white-space: normal; vertical-align: bottom; }
td.num, th.num { text-align: right; }
tr.is-current td { background: var(--accent-soft); }
tr.is-scheduled td { color: var(--muted); font-style: italic; }
.badge { display: inline-block; font-size: .7rem; font-weight: 700; font-style: normal; padding: 1px 7px; border-radius: 99px; margin-left: 6px; vertical-align: 1px; text-transform: uppercase; letter-spacing: .03em; }
.badge.current { background: var(--accent); color: var(--surface); }
.badge.scheduled { border: 1px solid var(--muted); color: var(--muted); }
.more-btn { font: inherit; margin-top: 12px; padding: 7px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-2); color: var(--text); cursor: pointer; }
.table-foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; }
.table-foot a { font-size: .9rem; }
.table-note { color: var(--muted); font-size: .85rem; margin: 10px 0 0; }
#history tbody tr[data-date] { cursor: pointer; }
#history tbody tr[data-date]:hover td { background: var(--surface-2); }
.math-head { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 10px; }
.math-head label { font-weight: 600; }
.math-head select { font: inherit; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-2); color: var(--text); }
.math td { white-space: normal; padding: 7px 8px; font-size: .92rem; }
.math td.num { white-space: nowrap; }
.math .src { color: var(--muted); font-size: .8rem; }
.math .op { display: inline-block; width: 1.3em; color: var(--muted); font-weight: 600; }
.math .grp td { font-weight: 600; padding-top: 16px; color: var(--muted); font-size: .8rem; text-transform: uppercase; letter-spacing: .03em; }
.math .sub td { font-weight: 600; }
.math .total td { font-weight: 700; border-top: 2px solid var(--text); }
.math-note { color: var(--muted); font-size: .85rem; margin: 12px 0 0; }
.chg-cell { white-space: normal; min-width: 220px; font-size: .85rem; }
.chg { margin: 1px 0; }
.chg .detail { color: var(--muted); font-variant-numeric: tabular-nums; }
.chg .src { white-space: nowrap; }
.chg .nosrc { color: var(--muted); font-style: italic; white-space: nowrap; }
.tou-card .hours { font-size: .8rem; color: var(--muted); margin-top: 2px; }

/* Explainers */
details { border-top: 1px solid var(--border); padding: 12px 0; }
details:first-of-type { border-top: 0; padding-top: 0; }
summary { cursor: pointer; font-weight: 600; }
details > div { padding-top: 6px; color: var(--text); }
details li { margin-bottom: 6px; }
.note { background: var(--note-bg); border-left: 4px solid var(--note-border); padding: 12px 14px; border-radius: 8px; font-size: .92rem; margin-bottom: 16px; }

footer { color: var(--muted); font-size: .85rem; margin-top: 28px; }
footer p { margin: 6px 0; }
</style>
</head>
<body>
<div class="wrap">

<header>
  <h1>Unofficial Duquesne Light Rate Tracker</h1>
  <p>What Duquesne Light (DLC) residential customers pay per kilowatt-hour: current rates, scheduled changes and history.</p>
  <p class="unofficial"><strong>Independent project, not affiliated with Duquesne Light Company.</strong> Figures are estimates; your DLC bill is the authoritative source.</p>
</header>

<div class="controls">
  <div>
    <span class="control-label" id="class-label">Rate class</span>
    <div class="seg" id="class-seg" role="group" aria-labelledby="class-label"></div>
  </div>
  <div>
    <span class="control-label" id="plan-label">Supply plan</span>
    <div class="seg" id="plan-seg" role="group" aria-labelledby="plan-label">
      <button type="button" data-plan="flat"><span class="code">Standard</span><span class="sub">Same price all day</span></button>
      <button type="button" data-plan="tou"><span class="code">Time-of-Use</span><span class="sub">Price varies by hour</span></button>
    </div>
  </div>
  <a class="help-link" href="#which-class">Which rate class am I?</a>
</div>

<noscript><div class="note">This page needs JavaScript to display rates. The raw data is available as <a href="https://github.com/pyther/dlc-rates/tree/main/output">CSV and JSON on GitHub</a>.</div></noscript>

<section class="card" id="summary" aria-live="polite"></section>

<section class="card" id="compare-card">
  <h2>Compared with past years</h2>
  <div id="compare"></div>
</section>

<section class="card">
  <h2>All rate changes</h2>
  <div class="table-scroll"><table id="history"></table></div>
  <p class="table-note" id="table-note" hidden>Change compares each rate with the previous rate <em>in the same season</em>, so switching between summer and winter rates isn't counted as a price change.</p>
  <div class="table-foot">
    <button type="button" class="more-btn" id="more-btn" hidden>Show all</button>
    <a href="https://github.com/pyther/dlc-rates/tree/main/output">Download CSV / JSON</a>
  </div>
</section>

<section class="card" id="math-card">
  <h2>How the rate is calculated</h2>
  <div id="math"></div>
</section>

<section class="card">
  <h2>About these numbers</h2>
  <div class="note">These are <strong>best-effort estimates</strong> built by hand from DLC's published tariffs. They may not match your bill exactly. DLC's official billing is always the authoritative source.</div>

  <details id="which-class">
    <summary>Which rate class am I?</summary>
    <div>
      <p>Your rate class is printed on your DLC bill. Most homes are on <strong>RS</strong>.</p>
      <ul>
        <li><strong>RS: Residential Service.</strong> Standard residential service.</li>
        <li><strong>RH: Residential Heating.</strong> Homes heated with electricity. Distribution is cheaper in winter (Nov–Apr).</li>
        <li><strong>RA: Residential Add-On Heat Pump.</strong> Homes with an add-on heat pump. Distribution is much cheaper in winter (Nov–Apr). Closed to new customers since January 1, 2025.</li>
      </ul>
    </div>
  </details>

  <details>
    <summary>How is the rate calculated?</summary>
    <div>
      <ul>
        <li><strong>Total rate:</strong> everything you pay per kWh: Price to Compare + Distribution.</li>
        <li><strong>Price to Compare (PTC):</strong> the cost of the electricity itself, i.e. DLC's default <em>Supply</em> charge plus <em>Transmission</em>. If you shop for a third-party supplier in Pennsylvania, this is the number to beat.</li>
        <li><strong>Distribution:</strong> the cost of delivering power to your home (poles, wires, infrastructure). You pay this to DLC no matter who supplies your electricity. DLC doesn't publish a single distribution rate, so this figure is the base rate combined with:
          <ul>
            <li>Rider No. 5: Universal Service Charge</li>
            <li>Rider No. 10: State Tax Adjustment</li>
            <li>Rider No. 15A: Phase IV Energy Efficiency and Conservation Surcharge</li>
            <li>Rider No. 22: Distribution System Improvement Charge (DSIC)</li>
          </ul>
        </li>
      </ul>
      <p>The bill estimate covers only these per-kWh charges. Your bill also includes a fixed monthly customer charge, which isn't shown here.</p>
    </div>
  </details>

  <details>
    <summary>Shopping for a third-party supplier?</summary>
    <div>
      <p>Pennsylvania lets you choose who supplies your electricity. Be careful: many offers start with a temporary "teaser" rate that later switches to an expensive variable rate, or they add monthly fees. Compare any offer against the current <strong>Price to Compare</strong> above, and check what happens when the introductory term ends.</p>
    </div>
  </details>

  <details>
    <summary>Is Time-of-Use worth it?</summary>
    <div>
      <p>In our view, Time-of-Use is a poor bet for most households. As the Time-of-Use cards above show, the Peak rate is roughly double the standard rate, while Off-Peak and Super Off-Peak save only a few cents per kWh. At current rates, using 1 kWh at Peak cancels out the savings from moving about 3 kWh to Super Off-Peak, or about 4 kWh to Off-Peak.</p>
      <p>That leaves little room for error. Even if you charge an EV overnight, a few peak-hour slips, like running the AC or doing laundry, can erase the savings. Before opting in, consider whether you can avoid peak-hour usage almost entirely.</p>
    </div>
  </details>

  <details>
    <summary>Sources and tariff archive</summary>
    <div>
      <ul>
        <li><a href="https://duquesnelight.com/service-reliability/service-map/rates/tariff-resources" target="_blank" rel="noopener noreferrer">DLC Tariff Resources</a></li>
        <li><a href="https://duquesnelight.com/service-reliability/service-map/rates/residential-rates" target="_blank" rel="noopener noreferrer">DLC Residential Rates</a></li>
        <li><a href="https://github.com/pyther/dlc-rates/blob/main/TARIFFS.md" target="_blank" rel="noopener noreferrer">Historical tariff archive</a> (DLC doesn't keep one publicly)</li>
      </ul>
    </div>
  </details>
</section>

<footer>
  <p>This is an independent project and is not affiliated with or endorsed by <a href="https://www.duquesnelight.com" target="_blank" rel="noopener noreferrer">Duquesne Light Company</a>. Data is provided "as is" for informational purposes only. For questions about your bill or service, contact DLC directly.</p>
  <p>Source on <a href="https://github.com/pyther/dlc-rates" target="_blank" rel="noopener noreferrer">GitHub</a> · Last built __BUILT__</p>
</footer>

</div>

<script>
const DATA = __RATE_DATA__;
const CLASSES = ["RS", "RH", "RA"];
const PERIODS = ["Peak", "Off-Peak", "Super Off-Peak"];
const PERIOD_VAR = { "Peak": "--peak", "Off-Peak": "--offpeak", "Super Off-Peak": "--superoff" };
// TOU period hours from Rider No. 8 – Default Service Supply (tariff page 98A).
const PERIOD_HOURS = { "Peak": "3–9 PM weekdays", "Off-Peak": "All other hours", "Super Off-Peak": "11 PM–6 AM every day" };
const INITIAL_ROWS = 12;
// DLC's own "typical residential customer" benchmark in its rate filings.
// (The Pennsylvania-wide average, per EIA, is closer to 800.)
const DEFAULT_KWH = "600";
const MAX_YEARS_BACK = 5;
const TODAY = (() => { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); })();

const state = { cls: "RS", plan: "flat", showAll: false, kwh: loadKwh(), mathDate: null };

// ---------- helpers ----------
const fmt = n => n.toFixed(2);
const kwhNum = () => Math.max(0, parseFloat(state.kwh) || 0);
// Cents-per-kWh → dollars per month at the visitor's usage.
function money(cents, signed) {
  const v = cents * kwhNum() / 100;
  const s = "$" + Math.abs(v).toFixed(2);
  if (!signed) return s;
  return Math.abs(v) < 0.005 ? "$0.00" : (v > 0 ? "+" : "−") + s;
}
// Dollar figures are rendered as <span data-cents="…" data-signed> so they can
// update live as the usage input changes, without re-rendering the page.
const moneySpan = (cents, signed) => `<span data-cents="${cents}"${signed ? " data-signed" : ""}>${money(cents, signed)}</span>`;
const kwhSpan = () => `<span class="kwh-label">${kwhNum().toLocaleString("en-US")}</span>`;
function refreshMoney() {
  document.querySelectorAll("[data-cents]").forEach(el => { el.textContent = money(parseFloat(el.dataset.cents), "signed" in el.dataset); });
  document.querySelectorAll(".kwh-label").forEach(el => { el.textContent = kwhNum().toLocaleString("en-US"); });
}
// Rate in effect on a given ISO date (rows are newest first).
const asOf = (rows, iso) => rows.find(r => r.date <= iso) || null;
// The previous rate in the same season (rows are newest first). For seasonal
// classes this keeps the May/Nov season switch from looking like a price change.
const prevSameSeason = (rows, r) => rows.slice(rows.indexOf(r) + 1).find(x => x.season === r.season) || null;
const yearsAgo = n => (parseInt(TODAY.slice(0, 4), 10) - n) + TODAY.slice(4);
const fmtDate = (iso, opts) => new Date(iso + "T00:00:00").toLocaleDateString("en-US", opts || { month: "short", day: "numeric", year: "numeric" });
const seasonNote = s => s === "Summer" ? "Summer rate (May–Oct)" : s === "Winter" ? "Winter rate (Nov–Apr)" : "";
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function deltaHtml(now, prev, suffix) {
  if (prev == null) return "";
  const d = now - prev;
  if (Math.abs(d) < 0.005) return `<span class="delta flat">no change${suffix || ""}</span>`;
  const pct = prev ? (d / prev) * 100 : 0;
  const cls = d > 0 ? "up" : "down";
  const arrow = d > 0 ? "▲" : "▼";
  return `<span class="delta ${cls}">${arrow} ${fmt(Math.abs(d))}¢ (${d > 0 ? "+" : "−"}${Math.abs(pct).toFixed(1)}%)${suffix || ""}</span>`;
}

// Split newest-first rows into scheduled (future), current, and past.
function split(rows) {
  const scheduled = rows.filter(r => r.date > TODAY);
  const rest = rows.filter(r => r.date <= TODAY);
  return { scheduled, current: rest[0] || rows[rows.length - 1], previous: rest[1] || null };
}

// ---------- controls ----------
function renderControls() {
  const seg = document.getElementById("class-seg");
  seg.innerHTML = CLASSES.map(c =>
    `<button type="button" data-cls="${c}" aria-pressed="${c === state.cls}"><span class="code">${c}</span><span class="sub">${esc(DATA[c].short)}</span></button>`
  ).join("");
  document.querySelectorAll("#plan-seg button").forEach(b => b.setAttribute("aria-pressed", b.dataset.plan === state.plan));
}

document.getElementById("class-seg").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  state.cls = b.dataset.cls; state.showAll = false; state.mathDate = null; update();
});
document.getElementById("plan-seg").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  state.plan = b.dataset.plan; state.showAll = false; state.mathDate = null; update();
});
document.querySelector(".help-link").addEventListener("click", e => {
  e.preventDefault();
  const det = document.getElementById("which-class");
  det.open = true; det.scrollIntoView({ behavior: "smooth", block: "start" });
});
document.getElementById("history").addEventListener("click", e => {
  const tr = e.target.closest("tr[data-date]");
  if (!tr || e.target.closest("a")) return;
  state.mathDate = tr.dataset.date; renderMath();
  document.getElementById("math-card").scrollIntoView({ behavior: "smooth", block: "start" });
});
document.getElementById("more-btn").addEventListener("click", () => { state.showAll = true; renderTable(); });

// ---------- summary ----------
function renderSummary() {
  const d = DATA[state.cls];
  const el = document.getElementById("summary");

  if (state.plan === "flat") {
    const { scheduled, current: cur } = split(d.flat);
    const prev = prevSameSeason(d.flat, cur);
    const sumParts = cur.ptc + cur.dist;
    const next = scheduled[scheduled.length - 1]; // soonest scheduled change
    const nextBase = next ? (prevSameSeason(d.flat, next) || cur) : null;
    const season = d.seasonal ? ` · ${seasonNote(cur.season)}` : "";

    el.innerHTML = `
      <div class="summary">
        <div>
          <p class="eyebrow">${esc(d.name)} (${state.cls}) · Standard rate</p>
          <div class="big">${fmt(cur.total)}<small>¢/kWh</small></div>
          <div class="meta">In effect since ${fmtDate(cur.date)}${season}</div>
          ${prev ? `<div class="meta">${deltaHtml(cur.total, prev.total)} vs. ${d.seasonal ? `last ${cur.season.toLowerCase()} rate (${fmtDate(prev.date)})` : fmtDate(prev.date)}</div>` : ""}        </div>
        <div class="parts">
          <div class="stackbar" aria-hidden="true">
            <span style="width:${(cur.ptc / sumParts) * 100}%;background:var(--ptc)"></span>
            <span style="width:${(cur.dist / sumParts) * 100}%;background:var(--dist)"></span>
          </div>
          <div>
            <div class="part-head"><span class="part-name"><span class="swatch" style="background:var(--ptc)"></span>Price to Compare</span><span class="part-val">${fmt(cur.ptc)}¢</span></div>
            <div class="part-desc">The electricity itself (supply ${fmt(cur.supply)}¢ + transmission ${fmt(cur.trans)}¢). A third-party supplier has to beat this.</div>
          </div>
          <div>
            <div class="part-head"><span class="part-name"><span class="swatch" style="background:var(--dist)"></span>Distribution</span><span class="part-val">${fmt(cur.dist)}¢</span></div>
            <div class="part-desc">Delivery to your home. You pay this to DLC whoever your supplier is.</div>
          </div>
        </div>
      </div>
      <div class="estimator">
        <label for="kwh">Monthly usage</label>
        <input id="kwh" type="number" inputmode="numeric" min="0" step="50" value="${esc(state.kwh)}"> kWh
        <span>≈ <span class="result">${moneySpan(cur.total)}</span> per month</span>
        <span class="fine">Per-kWh charges only, at today's rate. Excludes the fixed monthly customer charge. DLC's typical residential customer uses ${DEFAULT_KWH} kWh/month. Your bill shows yours.</span>
      </div>
      ${next ? `<div class="upcoming">📅 <strong>Scheduled change on ${fmtDate(next.date)}:</strong> total becomes <strong>${fmt(next.total)}¢/kWh</strong> ${deltaHtml(next.total, nextBase.total)}, about <strong>${moneySpan(next.total - nextBase.total, true)}/month</strong> at ${kwhSpan()} kWh${nextBase !== cur ? ` compared with the last ${next.season.toLowerCase()} rate` : ""}.</div>` : ""}`;

    document.getElementById("kwh").addEventListener("input", e => {
      state.kwh = e.target.value; saveKwh(state.kwh); refreshMoney();
    });
  } else {
    if (!d.tou.length) { el.innerHTML = `<p>No Time-of-Use rates are available for ${state.cls}.</p>`; return; }
    const { scheduled, current: cur } = split(d.tou);
    const flatCur = split(d.flat).current;
    const next = scheduled[scheduled.length - 1];
    const season = d.seasonal ? ` · ${seasonNote(cur.season)}` : "";

    const cards = PERIODS.map(p => {
      const r = cur.periods[p]; if (!r) return "";
      const vs = r.total - flatCur.total;
      return `<div class="tou-card" style="--c:var(${PERIOD_VAR[p]})">
        <div class="name">${p}</div>
        <div class="hours">${PERIOD_HOURS[p]}</div>
        <div class="val">${fmt(r.total)}<small> ¢/kWh</small></div>
        <div class="cmp">${vs >= 0 ? "+" : "−"}${fmt(Math.abs(vs))}¢ vs. standard rate</div>      </div>`;
    }).join("");

    el.innerHTML = `
      <p class="eyebrow">${esc(d.name)} (${state.cls}) · Time-of-Use rate</p>
      <div class="meta" style="margin:0 0 14px">In effect since ${fmtDate(cur.date)}${season} · Standard rate for comparison: ${fmt(flatCur.total)}¢/kWh</div>
      <div class="tou-grid">${cards}</div>
      ${next ? `<div class="upcoming">📅 <strong>Scheduled change on ${fmtDate(next.date)}:</strong> ${PERIODS.filter(p => next.periods[p]).map(p => `${p} <strong>${fmt(next.periods[p].total)}¢</strong>`).join(" · ")}</div>` : ""}
      <div class="meta" style="margin-top:14px">Peak excludes New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving and Christmas. Hours are from Rider No. 8 of DLC's tariff.</div>`;
  }
}

// ---------- table ----------
function rowState(r, current) {
  if (r.date > TODAY) return { cls: "is-scheduled", badge: '<span class="badge scheduled">Scheduled</span>' };
  if (r === current) return { cls: "is-current", badge: '<span class="badge current">Current</span>' };
  return { cls: "", badge: "" };
}

// "What changed" cell: each component that changed and the supplement behind it.
function changesHtml(r, kind) {
  const list = (DATA[state.cls].changes[r.date] || []).filter(c => c.kind === "common" || c.kind === kind);
  if (!list.length) return "—";
  return list.map(c => {
    const src = !c.source ? (c.detail ? ' · <span class="nosrc">source not recorded</span>' : "")
      : c.url ? ` · <a class="src" href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">Supp. ${esc(c.source)}</a>`
      : ` · <span class="src">Supp. ${esc(c.source)}</span>`;
    return `<div class="chg">${esc(c.label)}${c.detail ? ` <span class="detail">${esc(c.detail)}</span>` : ""}${src}</div>`;
  }).join("");
}

function renderTable() {
  const d = DATA[state.cls];
  const table = document.getElementById("history");
  const seasonTh = d.seasonal ? "<th>Season</th>" : "";
  let head, rows;

  if (state.plan === "flat") {
    const { current } = split(d.flat);
    head = `<tr><th>Effective</th>${seasonTh}<th class="num">Total ¢/kWh</th><th class="num">Change</th><th class="num">Price to Compare</th><th class="num">Distribution</th><th>What changed</th></tr>`;
    rows = d.flat.map((r, i) => {
      const prev = prevSameSeason(d.flat, r);
      const st = rowState(r, current);
      const ch = prev ? r.total - prev.total : null;
      const chHtml = ch == null ? "—" : Math.abs(ch) < 0.005 ? '<span class="delta flat">0.00</span>' :
        `<span class="delta ${ch > 0 ? "up" : "down"}">${ch > 0 ? "+" : "−"}${fmt(Math.abs(ch))}</span>`;
      return `<tr class="${st.cls}" data-date="${r.date}"><td>${fmtDate(r.date)}${st.badge}</td>${d.seasonal ? `<td>${r.season}</td>` : ""}<td class="num"><strong>${fmt(r.total)}</strong></td><td class="num">${chHtml}</td><td class="num">${fmt(r.ptc)}</td><td class="num">${fmt(r.dist)}</td><td class="chg-cell">${changesHtml(r, "flat")}</td></tr>`;
    });
  } else {
    const { current } = split(d.tou);
    head = `<tr><th>Effective</th>${seasonTh}${PERIODS.map(p => `<th class="num">${p}</th>`).join("")}<th class="num">Distribution</th><th>What changed</th></tr>`;
    rows = d.tou.map(r => {
      const st = rowState(r, current);
      return `<tr class="${st.cls}" data-date="${r.date}"><td>${fmtDate(r.date)}${st.badge}</td>${d.seasonal ? `<td>${r.season}</td>` : ""}${PERIODS.map(p => `<td class="num">${r.periods[p] ? fmt(r.periods[p].total) : "—"}</td>`).join("")}<td class="num">${fmt(r.dist)}</td><td class="chg-cell">${changesHtml(r, "tou")}</td></tr>`;
    });
  }

  const visible = state.showAll ? rows : rows.slice(0, INITIAL_ROWS);
  table.innerHTML = `<thead>${head}</thead><tbody>${visible.join("")}</tbody>`;
  const btn = document.getElementById("more-btn");
  btn.hidden = state.showAll || rows.length <= INITIAL_ROWS;
  document.getElementById("table-note").hidden = !(d.seasonal && state.plan === "flat");
  btn.textContent = `Show all ${rows.length} changes`;
}

// ---------- year-over-year comparison ----------
const signedC = v => (Math.abs(v) < 0.005 ? "±" : v > 0 ? "+" : "−") + fmt(Math.abs(v)) + "¢";
const agoLabel = n => n === 1 ? "1 year ago" : n + " years ago";

function renderCompare() {
  const d = DATA[state.cls];
  const card = document.getElementById("compare-card");
  const el = document.getElementById("compare");
  // Every whole year back the data covers (asOf() returns null past the oldest row).
  const horizons = Array.from({ length: MAX_YEARS_BACK }, (_, i) => i + 1);
  let cards = [], intro = "";

  if (state.plan === "flat") {
    const cur = split(d.flat).current;
    cards = horizons.map(n => {
      const iso = yearsAgo(n), then = asOf(d.flat, iso);
      if (!then) return "";
      const diff = cur.total - then.total;
      const dir = diff > 0.005 ? "up" : diff < -0.005 ? "down" : "";
      return `<div class="cmp-card">
        <div class="when">${agoLabel(n)} <span>(${fmtDate(iso)})</span></div>
        <div class="money-big ${dir}">${moneySpan(diff, true)}<small> /month</small></div>
        <div class="detail">${fmt(then.total)}¢ → ${fmt(cur.total)}¢/kWh ${deltaHtml(cur.total, then.total)}</div>
        <div class="detail">Price to Compare ${signedC(cur.ptc - then.ptc)} · Distribution ${signedC(cur.dist - then.dist)}</div>
      </div>`;
    }).filter(Boolean);
    intro = `How much more or less today's rate costs for ${kwhSpan()} kWh a month.` +
      (d.seasonal ? " Comparisons use the same calendar date, so the season matches." : "");
  } else if (d.tou.length) {
    const cur = split(d.tou).current;
    cards = horizons.map(n => {
      const iso = yearsAgo(n), then = asOf(d.tou, iso);
      if (!then) return "";
      const lines = PERIODS.filter(p => cur.periods[p] && then.periods[p]).map(p => {
        const now = cur.periods[p].total, was = then.periods[p].total;
        const pct = Math.round((now - was) / was * 1000) / 10; // 1 decimal, so "−0.0%" can't happen
        const dir = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
        const pctText = pct === 0 ? "no change" : `${pct > 0 ? "+" : "−"}${Math.abs(pct).toFixed(1)}%`;
        return `<div class="part-head" style="margin-top:6px"><span class="part-name"><span class="swatch" style="background:var(${PERIOD_VAR[p]})"></span>${p}</span><span class="delta ${dir}">${pctText}</span></div>
          <div class="detail">${fmt(was)}¢ → ${fmt(now)}¢/kWh (${signedC(now - was)})</div>`;
      }).join("");
      return `<div class="cmp-card"><div class="when">${agoLabel(n)} <span>(${fmtDate(iso)})</span></div>${lines}</div>`;
    }).filter(Boolean);
    intro = "Change in each period's rate compared with the same date in past years.";
  }

  card.hidden = cards.length === 0;
  el.innerHTML = `<p class="compare-intro">${intro}</p><div class="compare-grid">${cards.join("")}</div>`;
}

// ---------- calculation ----------
// Rebuilds the rate from its tariff inputs, in the same order as csv_rates.py.
const round4 = v => Math.round(v * 1e4) / 1e4;
const c4 = v => v.toFixed(4) + "¢";
const signed4 = v => (v < 0 ? "−" : "+") + Math.abs(v).toFixed(4) + "¢";
const pctFactor = v => `× (1 ${v < 0 ? "−" : "+"} ${Math.abs(v)}%)`;

function srcHtml(it) {
  const supp = !it.source ? '<span class="nosrc">source not recorded</span>'
    : it.url ? `<a href="${esc(it.url)}" target="_blank" rel="noopener noreferrer">Supp. ${esc(it.source)}</a>`
    : `Supp. ${esc(it.source)}`;
  return supp;
}

function mathRow(op, label, it, value, cls) {
  return `<tr class="${cls || ""}"><td><span class="op">${op}</span>${label}</td><td class="src">${it ? srcHtml(it) : ""}</td><td class="num">${value}</td></tr>`;
}

function renderMath() {
  const d = DATA[state.cls];
  const rows = state.plan === "flat" ? d.flat : d.tou;
  const el = document.getElementById("math");
  if (!rows.length) { el.innerHTML = ""; return; }
  if (!rows.some(r => r.date === state.mathDate)) state.mathDate = split(rows).current.date;
  const row = rows.find(r => r.date === state.mathDate);
  const c = d.calc[state.mathDate];
  const R = c.riders;

  const subtotal = c.base.value + R["Rider 5"].value + R["Rider 15A"].value;
  const withDsic = subtotal * (1 + R["Rider 22"].value / 100);
  const dist = round4(withDsic * (1 + R["Rider 10"].value / 100));

  let html = `<tr class="grp"><td colspan="3">Distribution</td></tr>` +
    mathRow("", esc(c.base.label), c.base, c4(c.base.value)) +
    mathRow("+", esc(R["Rider 5"].label), R["Rider 5"], c4(R["Rider 5"].value)) +
    mathRow("+", esc(R["Rider 15A"].label), R["Rider 15A"], c4(R["Rider 15A"].value)) +
    mathRow("=", "Subtotal", null, c4(subtotal), "sub") +
    mathRow("", `${pctFactor(R["Rider 22"].value)} ${esc(R["Rider 22"].label)}`, R["Rider 22"], signed4(withDsic - subtotal)) +
    mathRow("", `${pctFactor(R["Rider 10"].value)} ${esc(R["Rider 10"].label)}`, R["Rider 10"], signed4(dist - withDsic)) +
    mathRow("=", "Distribution", null, c4(dist), "sub");

  if (state.plan === "flat") {
    const ptc = c.supply.value + c.trans.value;
    const total = round4(ptc + dist);
    html += `<tr class="grp"><td colspan="3">Price to Compare</td></tr>` +
      mathRow("", esc(c.supply.label), c.supply, c4(c.supply.value)) +
      mathRow("+", esc(c.trans.label), c.trans, c4(c.trans.value)) +
      mathRow("=", "Price to Compare", null, c4(ptc), "sub") +
      mathRow("=", "Total: Price to Compare + Distribution", null, c4(total), "total");
  } else {
    html += `<tr class="grp"><td colspan="3">Price to Compare</td></tr>` +
      mathRow("", esc(c.trans.label), c.trans, c4(c.trans.value)) +
      PERIODS.filter(p => c.tou[p]).map(p => mathRow("", esc(c.tou[p].label), c.tou[p], c4(c.tou[p].value))).join("") +
      `<tr class="grp"><td colspan="3">Totals: supply + transmission + distribution</td></tr>` +
      PERIODS.filter(p => c.tou[p]).map(p => mathRow("=", `${p}: ${c4(c.tou[p].value)} + ${c4(c.trans.value)} + ${c4(dist)}`, null,
        c4(round4(c.tou[p].value + c.trans.value + dist)), "sub")).join("");
  }

  const options = rows.map(r => `<option value="${r.date}"${r.date === state.mathDate ? " selected" : ""}>${fmtDate(r.date)}${r.date > TODAY ? " (scheduled)" : r === split(rows).current ? " (current)" : ""}</option>`).join("");
  const shown = state.plan === "flat" ? `${fmt(row.total)}¢` : PERIODS.filter(p => row.periods[p]).map(p => `${p} ${fmt(row.periods[p].total)}¢`).join(", ");
  el.innerHTML = `
    <div class="math-head">
      <label for="math-date">Rate effective</label>
      <select id="math-date">${options}</select>
    </div>
    <div class="table-scroll"><table class="math">${html}</table></div>
    <p class="math-note">Shown elsewhere on this page rounded to two decimals: ${shown}. Click a row in the table above to see its calculation.</p>`;
  document.getElementById("math-date").addEventListener("change", e => { state.mathDate = e.target.value; renderMath(); });
}

// ---------- state / persistence ----------
// Only a value the visitor typed is stored; clearing the field or typing the
// default removes it, so a future change to DEFAULT_KWH still reaches them.
// (Key is versioned: an early build saved the old 800 default on every load.)
const KWH_KEY = "dlc-kwh-v2";
function loadKwh() { try { return localStorage.getItem(KWH_KEY) || DEFAULT_KWH; } catch (e) { return DEFAULT_KWH; } }
function saveKwh(v) {
  try {
    if (!v || v === DEFAULT_KWH) localStorage.removeItem(KWH_KEY);
    else localStorage.setItem(KWH_KEY, v);
  } catch (e) {}
}

function readHash() {
  const [cls, plan] = location.hash.replace("#", "").split("-");
  if (CLASSES.includes((cls || "").toUpperCase())) state.cls = cls.toUpperCase();
  if (plan === "tou" || plan === "flat") state.plan = plan;
}

function update() {
  const hash = `#${state.cls}-${state.plan}`;
  if (location.hash !== hash) history.replaceState(null, "", hash);
  renderControls();
  renderSummary();
  renderCompare();
  renderTable();
  renderMath();
}

readHash();
update();
window.addEventListener("hashchange", () => { const before = state.cls + state.plan; readHash(); if (state.cls + state.plan !== before) update(); });
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
