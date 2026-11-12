# AGENTS.md

Guidance for anyone (human or AI agent) updating this repository. It covers how the data is structured and how to add a new Duquesne Light (DLC) tariff supplement.

## What this project is

An unofficial tracker of DLC residential electricity rates (classes RS, RH, RA), published at https://pyther.net/dlc-rates/ from `docs/index.html`. Every rate on the site is calculated from values in DLC's tariff (Electric – Pa. P.U.C. No. 25), and every value cites the supplement that set it.

## Layout

| Path | What it is |
|---|---|
| `data/tariffs.csv` | Every supplement the data cites: number, issued and effective dates, what it changes, archive filename |
| `data/*.csv` | Rate components, one row per value change, each with a `Source` supplement |
| `csv_rates.py` | Loads and validates the data, builds the rate tables, works out what changed on each date |
| `generate_json.py` | Writes `output/rates.json` from the CSVs |
| `html_rates.py` | Generates `docs/index.html` (the whole site: HTML, CSS and JS in one template) |
| `output/` | Generated CSV/JSON, published for download. Commit these. |
| `docs/index.html` | Generated. **Never edit by hand**; edit `html_rates.py` and rebuild. |
| `TARIFFS.md` | Human-readable list of archived tariff documents |
| `build.sh` | Runs all three scripts. Always build after changing data or code. |

## How the rate is calculated

All values are in ¢/kWh unless marked %.

```
distribution = (base + Rider 5 + Rider 15A) × (1 + Rider 22 %) × (1 + Rider 10 %)
PTC          = supply (Rider 8) + transmission (Appendix A)
total        = distribution + PTC
```

Distribution is rounded to 4 decimals before adding the price to compare (PTC); the site shows 2 decimals. TOU uses the same distribution and transmission, with the period's supply rate instead of the flat one.

- **Seasons:** RH and RA have winter (Nov–Apr) and summer (May–Oct) base rates. The season is a calendar rule in `get_season()`, not tariff data, so the build adds May 1 and Nov 1 to the timeline automatically.
- **Excluded:** Rider 1 (a per-customer monthly charge, currently $0), Rider 20 (smart meter, $0), and the $13.00 monthly customer charge. Only per-kWh charges are in the rate.

## Data files

| File | Columns | Tariff page | Usual cadence |
|---|---|---|---|
| `supply.csv` | Effective Date, Rate, Source | Rider 8, p. 98A | Jun 1 and Dec 1 |
| `supply_tou.csv` | Effective Date, Period, Rate, Source | Rider 8, p. 98A | Jun 1 and Dec 1 (same supplement as supply) |
| `transmission.csv` | Effective Date, Class, Transmission, Source | Appendix A, p. 142 | Jun 1 (its own supplement, **not** the supply one) |
| `riders.csv` | Effective Date, Rider, Value, Unit, Source | see below | see below |
| `distribution_base.csv` | Effective Date, Class, Season, Base Rate, Source | RS p. 38, RH p. 40, RA p. 43 | Only in base rate cases |

`riders.csv` holds one row per rider change:

| Rider | Unit | Page | Usual cadence |
|---|---|---|---|
| `Rider 5`: Universal Service Charge | ¢/kWh | 93 | Jan 1 |
| `Rider 10`: State Tax Adjustment | % | 112 | Jan 1 |
| `Rider 15A`: Energy Efficiency & Conservation | ¢/kWh | 118 | Jun 1 |
| `Rider 22`: DSIC | % | 137 | Jan 1, Apr 1, Jul 1, Oct 1 |

Page numbers are the tariff's own page numbers (top right of each page), not PDF page numbers. They're only a guide for finding values in the PDFs; the code doesn't use them.

## Adding a supplement

1. **Get the filing.** DLC doesn't keep old supplements online, but the PA PUC has all of them:
   - Search the web for `"SUPP NO 112 TO PA PUC NO 25"` (with the right number), or browse DLC's dockets at https://www.puc.pa.gov/utility/110150.
   - Routine rate updates (supply, DSIC, transmission, Universal Service Charge, energy efficiency) are `M-` dockets. State Tax Adjustment updates and new riders are `R-` dockets. Base rate cases are `R-` dockets too.
   - Use DLC's own filing (titled e.g. "DSS RATE ADJ; SUPP NO 111 TO PA PUC NO 25"), not the PUC's secretarial letter ("… - SL").
   - Make sure the filing has real numbers. Some dockets hold an early filing whose rate tables are placeholders ("X.XX" or "X.XXXX") and a later rate-adjustment filing with the actual values. For Supp. 104, the April 1 filing has placeholders and the May 1 "ANNUAL EEC RATE ADJ" filing has the rates. Archive the one with the rates.

2. **Archive it.** Upload to the `tariff-25/` folder (not the bucket root) at `tariffs.pyther.net`:
   - `dlc-tariff-25-supp-N.pdf`: a single supplement filing. This is what `tariffs.csv` should link to.
   - `dlc-tariff-25-N.pdf`: a full tariff as of supplement N, if you also have one.

   Check it loads: `curl -sI https://tariffs.pyther.net/tariff-25/dlc-tariff-25-supp-N.pdf` should return 200.

   **Replacing an existing file:** Cloudflare caches these PDFs, so visitors keep getting the old version until the cache is purged (Cloudflare → Caching → Configuration → Purge Cache → Custom Purge, with the file's URL). A `curl -I` header check won't reveal this, because HEAD requests skip the cache. Compare full downloads instead; the sizes should match:
   ```bash
   u=https://tariffs.pyther.net/tariff-25/dlc-tariff-25-supp-N.pdf
   curl -s -o /dev/null -w '%{size_download}\n' "$u"          # what visitors get
   curl -s -o /dev/null -w '%{size_download}\n' "$u?v=$RANDOM" # what's stored
   ```

3. **Read page 2, "List of Modifications".** It lists exactly which pages and values the supplement changes. Only those values get new rows.

4. **Add the supplement to `data/tariffs.csv`:** number, issued date, effective date (from the page header, `YYYY-MM-DD`), a short description, and `Document` = the archive filename.

5. **Add one row per changed value** to the relevant data files, with `Source` = the supplement number and `Effective Date` = the supplement's effective date. Copy values exactly as printed (all 4 decimals).

6. **Update `TARIFFS.md`:** add an entry to "Supplements & Riders", newest first, matching the existing format.

7. **Run `./build.sh`** and check the output (see Verifying).

8. **Commit** data, outputs and `docs/index.html` together, e.g. `feat: update supply rates for Supplement No. 112 (effective 2027-06-01)`.

## Reading tariff values correctly

- **Parentheses mean negative.** "(0.0964%)" is −0.0964 and "($0.046297)" is −0.046297. The State Tax Adjustment has been negative since 2025.
- **Transmission is in $/kWh in the tariff.** Multiply by 100: $0.031841/kWh → `3.1841`.
- **Transmission and supply are separate filings.** Supply is Rider 8; transmission is Appendix A, updated in its own June supplement. Don't copy forward last year's transmission when entering a supply supplement.
- **Never copy forward unchanged values.** Only add rows for values the supplement actually changed. Unchanged components are looked up "as of" the date automatically.
- **Effective dates come from the page header** (`EFFECTIVE: …`), not the issue date. A supplement can be issued months before it takes effect; the site shows it as "Scheduled" until then.
- **Only residential classes matter.** Rider 8 also lists small/medium commercial and lighting rates (pages 98B–100); ignore them. Supplements that only change commercial rates (e.g. Rider 9, medium C&I supply) don't need data rows.
- **Each compiled tariff page names the supplement that last revised it** in its header ("SUPPLEMENT NO. 105 … EFFECTIVE: JUNE 1, 2026"). Use this to find the source of a value or to cross-check.

## Verifying

`./build.sh` stops with an error if:

- a `Source` isn't in `tariffs.csv`;
- a row's effective date doesn't match its supplement's effective date;
- a `Document` filename doesn't follow the naming pattern or can't contain that supplement;
- a rider name or unit in `riders.csv` is unknown.

It prints a note if any data rows have no `Source`. There should be none.

After building:

- Compare the new row in `output/rates.csv` with the previous one; the change should match what the supplement says (e.g. supply up 0.415¢ → total up 0.415¢).
- Open `docs/index.html` and check the "What changed" column and the "How the rate is calculated" card for the new date. Both should cite the new supplement and link to its PDF.
- Check every archive link loads:
  ```bash
  python3 -c "import csv_rates as c; print('\n'.join(sorted({t['URL'] for t in c.load_tariffs().values()})))" \
    | while read u; do curl -s -o /dev/null -w "%{http_code} $u\n" -I "$u"; done
  ```

## Things to leave alone without asking

- The "Unofficial" title and the disclaimer near the top of the page. They make clear the site isn't affiliated with DLC.
- Opinion text (e.g. the Time-of-Use section) should stay framed as opinion and backed by numbers on the page.
- The default usage of 600 kWh (`DEFAULT_KWH` in `html_rates.py`) is DLC's own "typical residential customer" figure.
- No DLC logos or brand colors.
