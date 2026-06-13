# entsoe-data-pipeline

This project is entsoe-data-pipeline: a local, file-based data ingestion tool for downloading selected
time-series datasets from the ENTSO-E API and persisting them as CSV/XLSX files.

The project is intentionally minimal and deterministic. It focuses on correctness,
clear separation of responsibilities, and reproducible outputs, without requiring databases, 
orchestration tools, cloud services, or analytics layers.

## Scope (MVP)

* Download data from the ENTSO-E API
* Support multiple logical datasets
* Persist data locally as CSV and/or XLSX
* Operate on explicit date ranges
* Ensure idempotent execution (skip existing outputs unless forced)

Out of scope:

* database-only storage as the primary workflow
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


### Time handling (UTC)

The project operates canonically in UTC:

- CLI dates are interpreted as UTC dates.
- All ENTSO-E API calls use explicit UTC-aware timestamps.
- Output indexes are named `timestamp_utc` and are stored as UTC-naive timestamps (semantically UTC) for Excel compatibility.

## Optional PostgreSQL storage

An optional PostgreSQL storage layer is available for importing existing CSV/XLSX outputs.
It does not replace the file-based pipeline.

PostgreSQL files:

- `sql/01_create_schemas.sql`
- `sql/02_create_tables.sql`
- `sql/03_create_indexes.sql`
- `sql/04_create_views.sql`
- `sql/05_validate_total_load.sql`
- `sql/06_validate_actual_generation.sql`
- `scripts/import_total_load_to_postgres.py`
- `scripts/import_actual_generation_to_postgres.py`

Use a local PostgreSQL database named `entsoe`. The importer reads connection settings from:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

Run the SQL scripts manually in order using pgAdmin Query Tool or `psql`:

```bash
psql -d entsoe -f sql/01_create_schemas.sql
psql -d entsoe -f sql/02_create_tables.sql
psql -d entsoe -f sql/03_create_indexes.sql
psql -d entsoe -f sql/04_create_views.sql
```

### Importing total_load

Preview an import without writing rows:

```bash
python scripts/import_total_load_to_postgres.py --dry-run
```

Run the import:

```bash
python scripts/import_total_load_to_postgres.py
```

The `entsoe_raw.total_load` table supports both hourly and 15-minute data in one table using `interval_minutes`.
The `timestamp_utc` column follows the project's UTC-naive storage convention, while `loaded_at` uses `TIMESTAMPTZ` for load metadata.

### Validating imported total_load data

After running the importer, validate the imported data manually in pgAdmin or `psql`:

```bash
psql -d entsoe -f sql/05_validate_total_load.sql
```

The validation script checks raw row counts, row counts by country and interval,
timestamp ranges, unsupported intervals, duplicate logical keys, NULL value summaries,
non-positive load values, daily completeness using the mart view, source file coverage,
and a quick mart preview.

### Importing actual_generation

Existing `actual_generation` CSV/XLSX outputs can be imported into `entsoe_raw.actual_generation`.
The importer converts the wide file output into a long/narrow PostgreSQL format for analytical querying.

In this model:

- `source_column` preserves the original CSV/XLSX column name.
- `production_type` is normalized for SQL-friendly analysis.
- `measurement_type` stores values such as `actual_aggregated` and `actual_consumption`.
- Legacy files without measurement suffixes are intentionally rejected and should be regenerated.

Preview an import without writing rows:

```bash
python scripts/import_actual_generation_to_postgres.py --dry-run
```

Run the import:

```bash
python scripts/import_actual_generation_to_postgres.py
```

After running the importer, validate the imported data manually in pgAdmin or `psql`:

```bash
psql -d entsoe -f sql/06_validate_actual_generation.sql
```

The `entsoe_mart.v_daily_actual_generation_by_type` view provides daily summaries by
country, interval, production type, and measurement type.


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
- UTC normalization (canonical UTC contract is enforced across all datasets via shared utilities; outputs use `timestamp_utc` and are stored as UTC-naive for Excel compatibility)
