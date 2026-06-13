import argparse
import logging
import os
import re
from pathlib import Path
from typing import Iterable

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


load_dotenv()

logger = logging.getLogger(__name__)

TIMESTAMP_COLUMN = "timestamp_utc"
SUPPORTED_SUFFIXES = {".csv", ".xlsx"}
MEASUREMENT_SUFFIXES = {
    "_actual_aggregated": "actual_aggregated",
    "_actual_consumption": "actual_consumption",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import existing actual_generation CSV/XLSX outputs into PostgreSQL."
    )
    parser.add_argument(
        "--input-dir",
        default="outputs/actual_generation",
        help="Directory containing actual_generation output files.",
    )
    parser.add_argument(
        "--country-code",
        default="PL",
        help="Country code to store with imported rows.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and validate files without inserting rows.",
    )
    return parser.parse_args()


def get_connection_settings() -> dict[str, str]:
    required_env_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    missing = [name for name in required_env_vars if not os.environ.get(name)]
    if missing:
        raise RuntimeError(
            "Missing required PostgreSQL environment variables: " + ", ".join(missing)
        )

    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": os.environ["POSTGRES_PORT"],
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def find_actual_generation_files(input_dir: Path) -> list[Path]:
    candidate_files = [
        path
        for path in input_dir.rglob("actual_generation_*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]

    selected_files: dict[Path, Path] = {}
    for path in sorted(candidate_files):
        logical_path = path.with_suffix("")
        existing_path = selected_files.get(logical_path)
        if existing_path is None or path.suffix.lower() == ".csv":
            selected_files[logical_path] = path

    return sorted(selected_files.values())


def read_actual_generation_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file extension for {path}")

    if TIMESTAMP_COLUMN not in df.columns:
        raise ValueError(f"{path} is missing required column: {TIMESTAMP_COLUMN}")

    value_columns = [column for column in df.columns if column != TIMESTAMP_COLUMN]
    if not value_columns:
        raise ValueError(f"{path} does not contain generation value columns")

    df = df[[TIMESTAMP_COLUMN, *value_columns]].copy()
    df[TIMESTAMP_COLUMN] = normalize_timestamp_values(df[TIMESTAMP_COLUMN], path)

    for column in value_columns:
        parse_generation_column(column, path)
        df[column] = pd.to_numeric(df[column], errors="raise")

    return df


def normalize_timestamp_values(values: pd.Series, source_file: Path) -> pd.Series:
    try:
        timestamps = pd.to_datetime(values, errors="raise")
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp_utc values in {source_file}") from exc

    if isinstance(timestamps.dtype, pd.DatetimeTZDtype):
        return timestamps.dt.tz_convert("UTC").dt.tz_localize(None)

    if timestamps.dtype == object:
        timestamps = pd.to_datetime(values, errors="raise", utc=True)
        return timestamps.dt.tz_convert("UTC").dt.tz_localize(None)

    return timestamps


def determine_interval_minutes(df: pd.DataFrame, source_file: Path) -> int:
    timestamps = (
        df[TIMESTAMP_COLUMN]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    if len(timestamps) < 2:
        raise ValueError(
            f"Cannot determine interval_minutes for {source_file}: "
            "at least two timestamps are required."
        )

    deltas = timestamps.diff().dropna()
    positive_deltas = deltas[deltas > pd.Timedelta(0)]
    if positive_deltas.empty:
        raise ValueError(
            f"Cannot determine interval_minutes for {source_file}: "
            "timestamps must contain a positive interval."
        )

    interval_minutes = int(positive_deltas.min().total_seconds() / 60)
    if interval_minutes <= 0 or 1440 % interval_minutes != 0:
        raise ValueError(
            f"Unsupported interval for {source_file}: {interval_minutes} minutes. "
            "Intervals must be positive and divide 1440 minutes cleanly."
        )

    unsupported_deltas = [
        int(delta.total_seconds() / 60)
        for delta in positive_deltas
        if int(delta.total_seconds() / 60) % interval_minutes != 0
    ]
    if unsupported_deltas:
        raise ValueError(
            f"Unsupported timestamp gaps for {source_file}: {unsupported_deltas}. "
            f"All gaps must be multiples of {interval_minutes} minutes."
        )

    return interval_minutes


def parse_generation_column(source_column: str, source_file: Path) -> tuple[str, str]:
    for suffix, measurement_type in MEASUREMENT_SUFFIXES.items():
        if source_column.endswith(suffix):
            raw_production_type = source_column[: -len(suffix)]
            production_type = normalize_production_type(
                raw_production_type, source_column, source_file,
            )
            return production_type, measurement_type

    supported_suffixes = ", ".join(sorted(MEASUREMENT_SUFFIXES))
    raise ValueError(
        f"Unsupported generation column in {source_file}: {source_column}. "
        f"Expected one of these suffixes: {supported_suffixes}. "
        "Legacy columns without measurement suffixes, such as 'biomass', "
        "are not supported. Regenerate the file using the current dataset output format."
    )


def normalize_production_type(
    value: str, source_column: str, source_file: Path,
) -> str:
    normalized_value = value.strip().lower()
    normalized_value = normalized_value.replace(" ", "_")
    normalized_value = normalized_value.replace("/", "_")
    normalized_value = normalized_value.replace("-", "_")
    normalized_value = re.sub(r"_+", "_", normalized_value)
    normalized_value = normalized_value.strip("_")

    if not normalized_value:
        raise ValueError(
            f"Invalid generation column in {source_file}: {source_column}. "
            "Normalized production type is empty."
        )

    return normalized_value


def build_rows(
    df: pd.DataFrame, country_code: str, interval_minutes: int, source_file: Path,
) -> list[tuple[object, ...]]:
    value_columns = [column for column in df.columns if column != TIMESTAMP_COLUMN]
    long_df = df.melt(
        id_vars=[TIMESTAMP_COLUMN],
        value_vars=value_columns,
        var_name="source_column",
        value_name="value_mw",
    )

    parsed_columns = {
        source_column: parse_generation_column(source_column, source_file)
        for source_column in value_columns
    }

    rows = []
    for record in long_df.itertuples(index=False):
        production_type, measurement_type = parsed_columns[record.source_column]
        rows.append(
            (
                country_code,
                record.timestamp_utc.to_pydatetime(),
                interval_minutes,
                production_type,
                measurement_type,
                record.source_column,
                none_if_nan(record.value_mw),
                str(source_file),
            )
        )

    ensure_no_normalized_key_collisions(rows, source_file)
    return rows


def ensure_no_normalized_key_collisions(
    rows: Iterable[tuple[object, ...]], source_file: Path,
) -> None:
    source_columns_by_key: dict[tuple[object, ...], set[str]] = {}

    for row in rows:
        logical_key = row[:5]
        source_column = str(row[5])
        source_columns_by_key.setdefault(logical_key, set()).add(source_column)

    collisions = [
        (logical_key, source_columns)
        for logical_key, source_columns in source_columns_by_key.items()
        if len(source_columns) > 1
    ]
    if not collisions:
        return

    logical_key, source_columns = collisions[0]
    (
        country_code,
        timestamp_utc,
        interval_minutes,
        production_type,
        measurement_type,
    ) = logical_key
    raise ValueError(
        "Normalized production type collision occurred in "
        f"{source_file}: country_code={country_code}, "
        f"timestamp_utc={timestamp_utc}, interval_minutes={interval_minutes}, "
        f"production_type={production_type}, measurement_type={measurement_type}, "
        f"source_columns={', '.join(sorted(source_columns))}"
    )


def none_if_nan(value: object) -> object:
    if pd.isna(value):
        return None
    return value


def insert_rows(connection: object, rows: Iterable[tuple[object, ...]]) -> None:
    sql = """
        INSERT INTO entsoe_raw.actual_generation (
            country_code,
            timestamp_utc,
            interval_minutes,
            production_type,
            measurement_type,
            source_column,
            value_mw,
            source_file
        )
        VALUES %s
        ON CONFLICT (
            country_code,
            timestamp_utc,
            interval_minutes,
            production_type,
            measurement_type
        )
        DO UPDATE SET
            source_column = EXCLUDED.source_column,
            value_mw = EXCLUDED.value_mw,
            source_file = EXCLUDED.source_file,
            loaded_at = now()
    """
    with connection.cursor() as cursor:
        execute_values(cursor, sql, rows)


def import_files(input_dir: Path, country_code: str, dry_run: bool) -> int:
    files = find_actual_generation_files(input_dir)
    logger.info(
        "Found %s actual_generation CSV/XLSX files in %s", len(files), input_dir
    )
    if not files:
        logger.warning("No actual_generation CSV/XLSX files found in %s", input_dir)
        return 0

    connection = None
    if not dry_run:
        connection = psycopg2.connect(**get_connection_settings())

    imported_rows = 0
    try:
        for path in files:
            logger.info("Reading %s", path)
            df = read_actual_generation_file(path)
            interval_minutes = determine_interval_minutes(df, path)
            rows = build_rows(df, country_code, interval_minutes, path)

            logger.info(
                "%s contains %s source rows and %s long rows with %s-minute interval",
                path,
                len(df),
                len(rows),
                interval_minutes,
            )

            if dry_run:
                logger.info("Dry run: validated %s without inserting rows", path)
            else:
                insert_rows(connection, rows)
                connection.commit()
                logger.info("Imported %s rows from %s", len(rows), path)

            imported_rows += len(rows)
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()

    return imported_rows


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    args = parse_args()

    try:
        total_rows = import_files(
            input_dir=Path(args.input_dir),
            country_code=args.country_code,
            dry_run=args.dry_run,
        )
    except Exception:
        logger.exception("Import failed")
        raise SystemExit(1)

    logger.info("Import completed successfully; rows processed=%s", total_rows)


if __name__ == "__main__":
    main()
