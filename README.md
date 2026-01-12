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

- **Day-ahead prices** — electricity market prices for Poland
- **Total load** — actual load and load forecast
- **Actual generation per production type** — full generation mix by source

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

## Execution

The project is executed via the single entrypoint:

```bash
python main.py --start YYYY-MM-DD --end YYYY-MM-DD
```

Optional flags:

* `--force` — overwrite existing outputs

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

## Development Notes

* Python dependencies must be installed in an isolated virtual environment.
* Generated data files and environment artifacts must not be committed.
* Architectural and operational rules for AI agents are defined in `AGENTS.md`.

## Project Status

This repository represents an MVP intended as a clean foundation for future
extensions (e.g. additional datasets, alternative storage backends, or orchestration),
without requiring refactoring of core architecture.

## Testing

The project includes a minimal unit test suite based on Python’s built-in `unittest` framework.

Tests are intentionally lightweight at the MVP stage and focus on core decision logic.  
As the project evolves, new functionality should be accompanied by appropriate unit tests.

