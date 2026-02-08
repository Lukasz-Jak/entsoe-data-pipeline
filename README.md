# entsoe-data-pipeline

This project is entsoe-data-pipeline: a local, file-based data ingestion tool for downloading selected
time-series datasets from the ENTSO-E API and persisting them as CSV/XLSX files.

The project is intentionally minimal and deterministic. It focuses on correctness,
clear separation of responsibilities, and reproducible outputs, without databases,
orchestration tools, cloud services, or analytics layers.

## Scope (MVP)

* Download data from the ENTSO-E API
* Support multiple logical datasets
* Persist data locally as CSV and/or XLSX
* Operate on explicit date ranges
* Ensure idempotent execution (skip existing outputs unless forced)

Out of scope:

* databases
* schedulers (cron, Airflow, etc.)
* cloud infrastructure
* analytics, reporting, or visualization

## Supported datasets (current)

The following datasets are currently implemented:

- Day-ahead prices
- Total load
- Actual generation per production type
- Generation forecast for wind & solar
- Generation forecast (day-ahead)
- Actual generation per generation unit
- Scheduled commercial exchanges (Intraday)
- Scheduled commercial exchanges (Day-Ahead)
- Cross-border physical flows



Each dataset is processed independently and stored as daily CSV/XLSX files.


## High-Level Architecture

* **API Client**
  Handles all communication with the ENTSO-E API, including retry and backoff logic.

* **Datasets**
  Each dataset represents one logical ENTSO-E data product and defines:

  * how data is fetched,
  * how it is normalized,
  * how output filenames are constructed.

* **Pipeline**
  Dataset-agnostic execution coordinator:

  * iterates over date ranges,
  * iterates over datasets,
  * orchestrates fetch → normalize → write.

* **IO Handler**
  Centralized file writing logic for CSV/XLSX outputs.

* **Entrypoint (`main.py`)**
  CLI parsing, configuration loading, and pipeline invocation only.

## Configuration

Configuration is externalized and loaded from:

* `config.yaml`
* environment variables (e.g. API key)

Secrets must not be committed to version control.

An example environment file is provided:

```
.env.example
```


### Scheduled Commercial Exchanges configuration

Scheduled Commercial Exchanges datasets (Intraday and Day-Ahead) require explicit configuration
of counterpart bidding zones in `config.yaml`:

```yaml
scheduled_commercial_exchanges:
  counterpart_areas:
    - DE
    - CZ
```
Each area code represents a bidding zone paired with Poland (PL).
For each configured zone, both directions are fetched automatically (PL → X and X → PL).

If no counterpart areas are configured, both datasets are skipped with a warning.


### Crossborder Physical Flows configuration

Crossborder Physical Flows dataset requires explicit configuration of counterpart bidding zones in `config.yaml`:

```yaml
crossborder_physical_flows:
  counterpart_areas:
    - DE
    - CZ
    - SK
```
Each area code represents a bidding zone paired with Poland (PL). For each configured zone, both directions are fetched automatically (PL → X and X → PL).

If no counterpart areas are configured, the dataset is skipped with a warning.





## Execution

The project is executed via the single entrypoint:

```bash
python main.py --start YYYY-MM-DD --end YYYY-MM-DD
```

Optional flags:
* --force — overwrite existing outputs
* --list-datasets — list available datasets and exit
* --datasets — comma-separated list of datasets to execute
* --dry-run — preview execution plan without downloading data or writing files

Examples:

List available datasets:
python main.py --list-datasets

Run only selected datasets:
python main.py --start 2025-01-01 --end 2025-01-03 --datasets TotalLoadDataset

Preview execution plan without side effects:
python main.py --start 2025-01-01 --end 2025-01-03 --dry-run


### Date range semantics

The pipeline uses a half-open date range: **[start_date, end_date)**.

This means:
- `--start` is inclusive
- `--end` is exclusive
- `--start` and `--end` must not be equal

To download data for a single day, the end date must be set to the **following day**.

Example (download data for 2024-01-01):

```bash
python main.py --start 2024-01-01 --end 2024-01-02
```

Using the same value for --start and --end will result in an empty dataset.


## Handling missing or delayed ENTSO-E data

Some ENTSO-E datasets (e.g. generation per unit) are published with delays
and may not be available for recent or future dates.

If no data is available for a given dataset and date:
- the dataset is skipped for that date,
- a warning is logged,
- no empty CSV/XLSX files are written,
- the pipeline continues processing other datasets and dates.

This behavior is intentional and prevents misleading “empty” outputs
from being treated as successfully downloaded data.


## Development Notes

* Python dependencies must be installed in an isolated virtual environment.
* Generated data files and environment artifacts must not be committed.
* Architectural and operational rules for AI agents are defined in `AGENTS.md`.

## Project Status

This repository represents an MVP intended as a clean foundation for future
extensions (e.g. additional datasets, alternative storage backends, or orchestration),
without requiring refactoring of core architecture.

## Testing

The project includes a unit test suite based on Python’s built-in `unittest` framework.

Tests are intentionally lightweight but cover:

- dataset fetch edge cases
- bidirectional exchange logic
- exception propagation
- deterministic output behavior
- UTC normalization (strict, defensive normalization is fully implemented for `crossborder_physical_flows`; other datasets currently rely on legacy behavior)
