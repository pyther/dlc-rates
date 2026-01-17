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

1.  **Generate CSV rates from source data:**
    ```bash
    python3 csv_rates.py
    ```
2.  **Convert CSV to JSON:**
    ```bash
    python3 generate_json.py
    ```
3.  **Generate the static HTML page:**
    ```bash
    python3 html_rates.py
    ```

## Disclaimer

These figures are not official and may not match your bill. **Duquesne Light Company is the sole authoritative source for billing and rate information.**
