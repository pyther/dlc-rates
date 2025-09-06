# Duquesne Light Company Rate Tracker

This project provides a **best-effort estimate** of Duquesne Light Company (DLC) residential electricity rates for RS, RA, and RH classes. All rates are shown in **¢/kWh** and include both flat and time-of-use (TOU) supply rates.

**Disclaimer:** Distribution rates are **not publicly published** by DLC. This project derives estimates from the DLC tariff and makes informed assumptions. Supply rates are taken from the published Price to Compare (PTC), which includes transmission charges. This page is for informational purposes only and may not match your actual bill. DLC’s billing and rates are the authoritative source.


## Usage

1. Generate CSV rates from source data:
   ```bash
   python3 csv_rates.py
   ```
2. Convert CSV to JSON:
   ```bash
   python3 generate_json.py
   ```
3. Generate Static HTML:
   ```bash
   python3 html_rates.py
   ```
