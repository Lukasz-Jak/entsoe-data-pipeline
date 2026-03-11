# AGENTS.md — OPERATIONAL CONTRACT (entsoe-data-pipeline)

## PROJECT INTENT

This project is entsoe-data-pipeline: a minimal, deterministic data ingestion pipeline for downloading
time-series data from the ENTSO-E API and persisting it to local files (CSV/XLSX).
It is intentionally limited in scope and designed to be correct, reproducible,
and extensible without introducing additional infrastructure.

## ABSOLUTE AUTHORITY
- Treat this file as the highest-priority repository contract.
- Follow these rules exactly. Do not reinterpret, relax, or “improve” constraints.
- Do not add features outside scope.
- Prefer determinism, safety, and architectural consistency over convenience.

## ENVIRONMENT & REPOSITORY HYGIENE

- All Python dependencies must be installed in an isolated virtual environment.
- Do not install Python packages globally.
- Do not assume the existence of a virtual environment unless explicitly stated.
- Do not modify the user's global Python environment.

- A `.gitignore` file must exist and must exclude:
  - virtual environments,
  - environment variable files,
  - local caches and build artifacts.
- Do not commit generated data files, secrets, or local environment artifacts.

## PROJECT SCOPE (MVP — HARD CONSTRAINTS)
- Language: Python.
- Purpose: download data from ENTSO-E API.
- Outputs: CSV and XLSX only.
- No databases.
- No schedulers/orchestrators (Airflow, cron integration, background jobs).
- No cloud services.
- No analytics/visualization layers.
- MVP must not block future expansion.

## GLOBAL RULES FOR AI AGENTS
- Follow AGENTS.md strictly.
- Do not introduce features outside the defined scope.
- Do not weaken or reinterpret constraints.
- Prefer clear separation of concerns over compactness.
- Avoid premature optimization and unnecessary abstractions.
- Do not duplicate logic across modules.
- Do not hardcode configuration values.
- Use explicit types (type hints) for public functions/classes and key internal boundaries.
- Maintain stable public interfaces; avoid breaking changes unless explicitly instructed.

## TECHNOLOGY & DESIGN FREEZE (DECISION FREEZE)
- Treat all current architectural choices, patterns, and technology selections as frozen.
- Do not replace libraries, introduce alternatives, or “modernize” the stack unless explicitly instructed.
- Do not introduce async/concurrency patterns, new frameworks, or new paradigms.
- Do not refactor for stylistic or personal preference reasons.
- Any change to core architectural decisions requires explicit user instruction.

## PROJECT STRUCTURE RULES
- Use a `src/` directory.
- Code must be organized by logical responsibility.
- A Python file may contain multiple related functions or classes,
  but must address a single, clearly defined responsibility.
- API access, pipeline control, IO, and transformations must be separated.
- No direct HTTP / entsoe-py API calls outside the API client module.
  Datasets are expected to call the provided client.fetch_data(...) interface — this is correct and intentional.

- No IO logic inside dataset definitions.

## ENTRYPOINT RULES
- `main.py` is the only execution entrypoint.
- `main.py` may:
  - parse CLI arguments,
  - load configuration,
  - invoke the pipeline.
- `main.py` must not contain business logic.

## PIPELINE RULES
- Pipeline coordinates execution flow only.
- Pipeline:
  - iterates over date ranges,
  - iterates over datasets,
  - orchestrates fetch → normalize → write.
- Pipeline must remain dataset-agnostic.
- Pipeline must not implement API-specific or file-format-specific logic.
- Pipeline must not contain error recovery, retry, or backoff logic.
  Controlled skipping of missing datasets (e.g. NoMatchingDataError, missing formats) is intentional and part of normal pipeline flow.

## DATASET RULES
- Each dataset represents one logical ENTSO-E data product.
- Dataset definitions encapsulate:
  - how data is fetched (via API client),
  - how data is normalized,
  - how output filenames are constructed.
- Dataset logic is domain-specific.
- Pipeline logic must not change when adding a new dataset.

## TIME HANDLING RULES

### Canonical Time Contract (MANDATORY)

- Canonical in-memory time representation is UTC.
- All API queries must use explicit UTC-aware timestamps.
- All dataset indexes must represent UTC.
- Stored outputs must use index/column name: `timestamp_utc`.
- Stored timestamps are UTC-naive for Excel compatibility, but semantically UTC.

Timezone stripping is allowed ONLY at the storage boundary.

UTC is the single source of truth.
Any future local-time representations (e.g. Europe/Warsaw) must be derived from canonical UTC data.

### Index Normalization

A shared utility function must be used for all dataset index normalization (located in `src/utils.py`):

    ensure_utc_index(df: pd.DataFrame, make_naive_for_storage: bool = True)

This function is responsible for:

- guaranteeing DatetimeIndex
- enforcing UTC
- handling:
  - non-datetime index
  - tz-aware index
  - tz-naive index
- optionally stripping timezone for storage
- setting index name to `timestamp_utc`

Dataset-specific normalization logic must NOT duplicate this behavior.


### Refactoring Policy

- Canonical UTC time handling is now implemented across all existing datasets.
- Any new dataset MUST:
  - pass UTC-aware `pd.Timestamp` to the ENTSO-E client
  - normalize indexes exclusively via `ensure_utc_index(...)`
- Agents must NOT introduce duplicate time normalization logic.

No silent assumptions about tz-naive meaning UTC are allowed outside the shared utility.
Do NOT add or modify tests during implementation work; tests are introduced only in a separate session when explicitly requested.


## FILE OUTPUT RULES
- Allowed output formats: CSV, XLSX.
- File writing logic must be centralized.
- Output paths must be deterministic and date-partitioned.
- Column naming conventions must be consistent across datasets.
- Pipeline must interact with outputs via a generic writer interface.

## IDEMPOTENCY RULES
- Default behavior: skip writing outputs that already exist.
- Existence checks must occur before writing.
- A `--force` flag must explicitly allow overwriting existing data.
- Skip vs overwrite decisions must be logged.
- Idempotency safeguards must never be bypassed.

## LOGGING RULES
- Use Python's `logging` module.
- Do not use `print()` in core logic.
- Log at minimum:
  - dataset name,
  - date (or date range unit),
  - execution status (success / skipped / failed).
- Log failures with stack traces using `logger.exception(...)`.
- Never log secrets or sensitive configuration values.

## API CLIENT RULES
- All ENTSO-E interactions must go through a dedicated API client module.
- Retry logic must exist only in the API client.
- Use configurable exponential backoff.
- Pipeline and datasets must not implement retry, sleep, or backoff logic.

## ERROR HANDLING PHILOSOPHY
- API client:
  - handles network errors, HTTP errors, and retry/backoff.
  - does NOT retry on ENTSO-E `NoMatchingDataError` (missing data is not a technical failure).
  - re-raises `NoMatchingDataError` immediately.
- Dataset layer:
  - handles domain-level semantics (e.g. missing or delayed ENTSO-E data).
  - may catch `NoMatchingDataError`, log a warning, and skip the affected date.
  - must not silently swallow unexpected exceptions.

- Pipeline:
  - captures execution outcome (success / skipped / failed).
  - logs failures with context.
  - does not silently ignore errors.
- Do not add defensive try/except blocks without explicit purpose.

## SECURITY RULES
- API keys and secrets must never be stored in source code.
- Secrets must be loaded from environment variables or external config.
- `.env` files must not be committed to version control.
- Do not log secrets or sensitive configuration values.

## CONFIGURATION RULES
- Configuration must be externalized (e.g. YAML + environment variables).
- CLI arguments override configuration values.
- No hardcoded credentials, paths, or dates.
- Configuration loading must support environment-based overrides for secrets.

## CODE STYLE & READABILITY CONTRACT
- Prioritize clarity and maintainability over brevity.
- Prefer small, single-responsibility functions.
- Avoid “clever” Python constructs that reduce readability.
- Do not refactor purely for stylistic preference.
- Code must be understandable without external explanation.

## EXPLICIT NON-GOALS
This project explicitly does NOT aim to:
- optimize performance beyond basic correctness,
- minimize API calls beyond required functionality,
- deduplicate or reconcile historical datasets,
- support real-time or streaming data processing,
- provide analytics, reporting, or visualization features.

## FUTURE-PROOFING RULES
- Do not assume CSV/XLSX are the final storage layer.
- Do not tightly couple pipeline logic to file formats.
- Design code so future support for:
  - larger time ranges (e.g. monthly),
  - orchestration tools (e.g. Airflow),
  - database storage,
can be added without refactoring core architecture.

## FORBIDDEN ACTIONS (ABSOLUTE)
AI agents must NOT:
- introduce databases,
- introduce schedulers or background jobs,
- introduce concurrency or async execution,
- introduce new storage formats,
- bypass idempotency safeguards,
- refactor architecture without explicit instruction.

## AGENTS.MD MODIFICATION
AI agents must not modify AGENTS.md unless explicitly instructed by the user.
If a task conflicts with AGENTS.md, the agent must stop and ask for guidance.

## Language conventions

All source code, log messages, error messages, CLI output, comments, and user-facing communication **must be written in English**.

This rule applies to:
- logging messages
- exceptions and error texts
- CLI help and validation messages
- documentation generated or modified by the agent

Do not introduce user-facing messages in any other language.


## Testing expectations

The project uses Python's built-in `unittest` framework (NOT pytest).

Testing workflow is split into separate sessions:
- During implementation sessions: do NOT add or modify tests unless explicitly requested by the user.
- During testing sessions (explicitly requested): add/update tests as needed.

If tests are run and fail after implementing requested behavior:
- STOP and report what failed.
- Do NOT change architectural decisions or production logic to satisfy outdated tests.
- Do NOT modify tests unless explicitly instructed by the user.

