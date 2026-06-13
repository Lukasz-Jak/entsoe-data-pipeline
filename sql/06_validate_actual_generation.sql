-- Validate imported actual_generation data in PostgreSQL.
-- This script is read-only and does not modify data.
-- Run it manually after importing local actual_generation outputs into PostgreSQL.

-- 1. Raw table row count
-- Shows the total number of imported rows.
SELECT
    COUNT(*) AS total_rows
FROM entsoe_raw.actual_generation;

-- 2. Raw row count by country, interval, production type, and measurement type
-- Confirms how many rows were imported for each generation series.
SELECT
    country_code,
    interval_minutes,
    production_type,
    measurement_type,
    COUNT(*) AS total_rows
FROM entsoe_raw.actual_generation
GROUP BY
    country_code,
    interval_minutes,
    production_type,
    measurement_type
ORDER BY
    country_code,
    interval_minutes,
    production_type,
    measurement_type;

-- 3. Raw timestamp range
-- Shows imported UTC timestamp coverage for each country and time resolution.
SELECT
    country_code,
    interval_minutes,
    MIN(timestamp_utc) AS min_timestamp_utc,
    MAX(timestamp_utc) AS max_timestamp_utc
FROM entsoe_raw.actual_generation
GROUP BY
    country_code,
    interval_minutes
ORDER BY
    country_code,
    interval_minutes;

-- 4. Unsupported intervals
-- Detects rows with invalid interval lengths; this should normally return zero rows.
SELECT
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type,
    source_column,
    value_mw,
    source_file,
    loaded_at
FROM entsoe_raw.actual_generation
WHERE
    interval_minutes <= 0
    OR 1440 % interval_minutes <> 0
ORDER BY
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type;

-- 5. Duplicate logical keys
-- Detects duplicate records for the natural actual_generation key; this should normally return zero rows.
SELECT
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type,
    COUNT(*) AS duplicate_count
FROM entsoe_raw.actual_generation
GROUP BY
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type
HAVING COUNT(*) > 1
ORDER BY
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type;

-- 6. NULL value summary
-- Counts missing generation values by generation series.
SELECT
    country_code,
    interval_minutes,
    production_type,
    measurement_type,
    COUNT(*) FILTER (WHERE value_mw IS NULL) AS null_value_rows
FROM entsoe_raw.actual_generation
GROUP BY
    country_code,
    interval_minutes,
    production_type,
    measurement_type
ORDER BY
    country_code,
    interval_minutes,
    production_type,
    measurement_type;

-- 7. Negative generation values
-- Detects negative generation values; this should normally return zero rows.
SELECT
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type,
    source_column,
    value_mw,
    source_file,
    loaded_at
FROM entsoe_raw.actual_generation
WHERE value_mw < 0
ORDER BY
    country_code,
    timestamp_utc,
    interval_minutes,
    production_type,
    measurement_type;

-- 8. Daily completeness using the mart view
-- Detects days where the row count does not match the expected interval count.
SELECT
    country_code,
    delivery_date,
    interval_minutes,
    production_type,
    measurement_type,
    records_count,
    1440 / interval_minutes AS expected_rows,
    'CHECK' AS status
FROM entsoe_mart.v_daily_actual_generation_by_type
WHERE records_count <> 1440 / interval_minutes
ORDER BY
    delivery_date,
    country_code,
    production_type,
    measurement_type,
    interval_minutes;

-- 9. Source file coverage
-- Shows row counts and UTC timestamp coverage by source file.
SELECT
    source_file,
    COUNT(*) AS total_rows,
    MIN(timestamp_utc) AS min_timestamp_utc,
    MAX(timestamp_utc) AS max_timestamp_utc
FROM entsoe_raw.actual_generation
GROUP BY source_file
ORDER BY source_file;

-- 10. Production type coverage
-- Lists distinct generation series loaded into the raw table.
SELECT DISTINCT
    production_type,
    measurement_type,
    source_column
FROM entsoe_raw.actual_generation
ORDER BY
    production_type,
    measurement_type,
    source_column;

-- 11. Quick mart preview
-- Displays a small sample from the daily actual_generation mart view.
SELECT
    country_code,
    delivery_date,
    interval_minutes,
    production_type,
    measurement_type,
    records_count,
    non_null_values_count,
    avg_value_mw,
    min_value_mw,
    max_value_mw,
    estimated_mwh
FROM entsoe_mart.v_daily_actual_generation_by_type
ORDER BY
    delivery_date,
    country_code,
    production_type,
    measurement_type,
    interval_minutes
LIMIT 20;
