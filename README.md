# Duquesne Light Company Rate Tracker

This project tracks Duquesne Light Company (DLC) residential electricity rates for classes RS, RA, and RH. Its primary objective is to consolidate complex, multi-layered tariff data into a clear and usable format.

All rates are presented in **cents per kilowatt-hour (¢/kWh)** and include both flat-rate and time-of-use (TOU) supply figures.

For a summary of current and historical rates, see the [DLC rates table](https://pyther.net/dlc-rates/).

## Why This Project Exists

Official DLC tariffs provide the raw data required for billing, but calculating a total price per kWh is a complex process. The final rate is a composite of supply charges, distribution base rates, and various riders and surcharges (such as Rider 5, Rider 10, and Rider 15A). 

By aggregating these individual components, this project provides a simplified, single-figure estimate of the total cost per kWh.

## Historical Tariffs

DLC does not maintain a public archive of past filings. A collection of historical tariff documents used for this project is available in the [Tariff Archive](./TARIFFS.md).

## Usage

Run `./build.sh` to regenerate everything. It runs these three steps in order:

1.  `python3 csv_rates.py`: builds `output/rates.csv` and `output/rates_tou.csv` from `data/`
2.  `python3 generate_json.py`: converts them to `output/rates.json`
3.  `python3 html_rates.py`: generates the site at `docs/index.html`

## Adding a Tariff Supplement

Every rate value in `data/` names the supplement that set it, so each change on the site links back to a DLC filing.

1. Upload the PDF to `tariffs.pyther.net/tariff-25/` as `dlc-tariff-25-supp-N.pdf` (a supplement on its own) or `dlc-tariff-25-N.pdf` (the full tariff as of Supplement N). Then add the supplement to `data/tariffs.csv` with its issued and effective dates, what it changes, and that filename in `Document`.
2. Add one row for each value it changed, with the supplement number in the `Source` column:
   - Supply (Rider 8): `supply.csv` and `supply_tou.csv`
   - Transmission (Appendix A): `transmission.csv`
   - Riders 5, 10, 15A and 22: `riders.csv` (one row per rider; `Unit` is `¢/kWh` or `%`)
   - Base distribution rates: `distribution_base.csv`
3. Run `./build.sh`. The build stops if a `Source` isn't in `tariffs.csv` or its effective date doesn't match the supplement's.

Each supplement's page 2 ("List of Modifications") lists exactly which values it changes.

See [AGENTS.md](./AGENTS.md) for the full process, including where to find old supplements on the PUC site and how to read tariff values correctly.

## Disclaimer

These figures are not official and may not match your bill. **Duquesne Light Company is the sole authoritative source for billing and rate information.**
