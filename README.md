# Duquesne Light Company Rate Tracker

This project provides **best-effort estimates** of Duquesne Light Company (DLC) residential electricity rates for classes RS, RA, and RH. The goal is to consolidate complex tariff information into a clear, usable format.

All rates are shown in **cents per kilowatt-hour (¢/kWh)** and include both standard (flat) and time-of-use (TOU) supply rates.

## How It Works

Official DLC tariff documents don't directly reflect the final amount on a customer's bill due to numerous riders and surcharges. This project estimates the final rate by:

* **Supply Rates:** Using the official, published **Price to Compare (PTC)**, which includes generation and transmission charges.
* **Distribution Rates:** Analyzing the complete tariff documents to derive an estimated distribution cost, accounting for all applicable riders (e.g., Rider 5, Rider 10, Rider 15A).

Updates are currently performed manually by monitoring DLC for new tariff filings, updating the source data, and regenerating the rate files.


## Disclaimer

The rates provided here are for **informational purposes only** and are not official figures. They are best-effort estimates and may not exactly match your bill. **Duquesne Light Company's official billing and rate information are the sole authoritative sources.**


## Historical Tariffs

DLC does not provide a public archive of past tariff documents. For reference, copies of the historical tariffs used in this project are hosted [here](https://archive.pyther.net/dlc-tariffs/).

## Usage

1.  Generate CSV rates from source data:
    ```bash
    python3 csv_rates.py
    ```
2.  Convert CSV to JSON:
    ```bash
    python3 generate_json.py
    ```
3.  Generate the static HTML page:
    ```bash
    python3 html_rates.py
    ```
