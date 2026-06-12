import argparse
import logging
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


load_dotenv()

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"timestamp_utc", "actual_load", "forecast_load"}
SUPPORTED_SUFFIXES = {".csv", ".xlsx"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import existing total_load CSV/XLSX outputs into PostgreSQL."
    )
    parser.add_argument(
        "--input-dir",
        default="outputs/total_load",
        help="Directory containing total_load output files.",
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
            "Missing required PostgreSQL environment variables: "
            + ", ".join(missing)
        )

    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": os.environ["POSTGRES_PORT"],
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def find_total_load_files(input_dir: Path) -> list[Path]:
    candidate_files = [
        path
        for path in input_dir.rglob("total_load_*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]

    selected_files: dict[Path, Path] = {}
    for path in sorted(candidate_files):
        logical_path = path.with_suffix("")
        existing_path = selected_files.get(logical_path)
        if existing_path is None or path.suffix.lower() == ".csv":
            selected_files[logical_path] = path

    return sorted(selected_files.values())


def read_total_load_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    elif path.suffix.lower() == ".xlsx":
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file extension for {path}")

    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"{path} is missing required columns: {', '.join(sorted(missing_columns))}"
        )

    df = df[["timestamp_utc", "actual_load", "forecast_load"]].copy()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="raise")
    return df


def normalize_timestamp_column(df: pd.DataFrame) -> pd.DataFrame:
    timestamps = df["timestamp_utc"]
    if timestamps.dt.tz is not None:
        df["timestamp_utc"] = timestamps.dt.tz_convert("UTC").dt.tz_localize(None)

    return df


def determine_interval_minutes(df: pd.DataFrame, source_file: Path) -> int:
    timestamps = (
        df["timestamp_utc"]
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
    if interval_minutes not in (15, 60):
        raise ValueError(
            f"Unsupported interval for {source_file}: {interval_minutes} minutes. "
            "Only 15-minute and hourly data are supported."
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


def build_rows(
    df: pd.DataFrame,
    country_code: str,
    interval_minutes: int,
    source_file: Path,
) -> list[tuple[object, ...]]:
    rows = []
    for record in df.itertuples(index=False):
        rows.append(
            (
                country_code,
                record.timestamp_utc.to_pydatetime(),
                interval_minutes,
                none_if_nan(record.actual_load),
                none_if_nan(record.forecast_load),
                str(source_file),
            )
        )
    return rows


def none_if_nan(value: object) -> object:
    if pd.isna(value):
        return None
    return value


def insert_rows(connection: object, rows: Iterable[tuple[object, ...]]) -> None:
    sql = """
        INSERT INTO entsoe_raw.total_load (
            country_code,
            timestamp_utc,
            interval_minutes,
            actual_load_mw,
            forecast_load_mw,
            source_file
        )
        VALUES %s
        ON CONFLICT (country_code, timestamp_utc, interval_minutes)
        DO UPDATE SET
            actual_load_mw = EXCLUDED.actual_load_mw,
            forecast_load_mw = EXCLUDED.forecast_load_mw,
            source_file = EXCLUDED.source_file,
            loaded_at = now()
    """
    with connection.cursor() as cursor:
        execute_values(cursor, sql, rows)


def import_files(input_dir: Path, country_code: str, dry_run: bool) -> int:
    files = find_total_load_files(input_dir)
    if not files:
        logger.warning("No total_load CSV/XLSX files found in %s", input_dir)
        return 0

    connection = None
    if not dry_run:
        connection = psycopg2.connect(**get_connection_settings())

    imported_rows = 0
    try:
        for path in files:
            logger.info("Reading %s", path)
            df = normalize_timestamp_column(read_total_load_file(path))
            interval_minutes = determine_interval_minutes(df, path)
            rows = build_rows(df, country_code, interval_minutes, path)

            if dry_run:
                logger.info(
                    "Dry run: %s contains %s rows with %s-minute interval",
                    path,
                    len(rows),
                    interval_minutes,
                )
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
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
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
