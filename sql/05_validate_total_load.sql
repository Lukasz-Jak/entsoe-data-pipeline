-- Validate imported total_load data in PostgreSQL.
-- This script is read-only and does not modify data.
-- Run it manually after importing local total_load outputs into PostgreSQL.

-- 1. Raw table row count
-- Shows the total number of imported rows.
SELECT
    COUNT(*) AS total_rows
FROM entsoe_raw.total_load;

-- 2. Raw row count by country and interval
-- Confirms how many rows were imported for each country and time resolution.
SELECT
    country_code,
    interval_minutes,
    COUNT(*) AS total_rows
FROM entsoe_raw.total_load
GROUP BY
    country_code,
    interval_minutes
ORDER BY
    country_code,
    interval_minutes;

-- 3. Raw timestamp range
-- Shows the imported UTC timestamp coverage for each country and time resolution.
SELECT
    country_code,
    interval_minutes,
    MIN(timestamp_utc) AS min_timestamp_utc,
    MAX(timestamp_utc) AS max_timestamp_utc
FROM entsoe_raw.total_load
GROUP BY
    country_code,
    interval_minutes
ORDER BY
    country_code,
    interval_minutes;

-- 4. Unsupported intervals
-- Detects rows with unexpected interval lengths; this should normally return zero rows.
SELECT
    country_code,
    timestamp_utc,
    interval_minutes,
    actual_load_mw,
    forecast_load_mw,
    source_file,
    loaded_at
FROM entsoe_raw.total_load
WHERE interval_minutes NOT IN (15, 60)
ORDER BY
    country_code,
    timestamp_utc,
    interval_minutes;

-- 5. Duplicate logical keys
-- Detects duplicate records for the natural total_load key; this should normally return zero rows.
SELECT
    country_code,
    timestamp_utc,
    interval_minutes,
    COUNT(*) AS duplicate_count
FROM entsoe_raw.total_load
GROUP BY
    country_code,
    timestamp_utc,
    interval_minutes
HAVING COUNT(*) > 1
ORDER BY
    country_code,
    timestamp_utc,
    interval_minutes;

-- 6. NULL value summary
-- Counts missing actual and forecast load values by country and time resolution.
SELECT
    country_code,
    interval_minutes,
    COUNT(*) FILTER (WHERE actual_load_mw IS NULL) AS null_actual_load_rows,
    COUNT(*) FILTER (WHERE forecast_load_mw IS NULL) AS null_forecast_load_rows
FROM entsoe_raw.total_load
GROUP BY
    country_code,
    interval_minutes
ORDER BY
    country_code,
    interval_minutes;

-- 7. Non-positive load values
-- Detects zero or negative load values; this should normally return zero rows.
SELECT
    country_code,
    timestamp_utc,
    interval_minutes,
    actual_load_mw,
    forecast_load_mw,
    source_file,
    loaded_at
FROM entsoe_raw.total_load
WHERE
    actual_load_mw <= 0
    OR forecast_load_mw <= 0
ORDER BY
    country_code,
    timestamp_utc,
    interval_minutes;

-- 8. Daily completeness using the mart view
-- Detects days where the row count does not match the expected interval count.
SELECT
    country_code,
    delivery_date,
    interval_minutes,
    records_count,
    CASE
        WHEN interval_minutes = 60 THEN 24
        WHEN interval_minutes = 15 THEN 96
        ELSE NULL
    END AS expected_rows,
    'CHECK' AS status
FROM entsoe_mart.v_daily_total_load_summary
WHERE
    interval_minutes NOT IN (15, 60)
    OR records_count <> CASE
        WHEN interval_minutes = 60 THEN 24
        WHEN interval_minutes = 15 THEN 96
    END
ORDER BY
    delivery_date,
    country_code,
    interval_minutes;

-- 9. Source file coverage
-- Shows row counts and UTC timestamp coverage by source file.
SELECT
    source_file,
    COUNT(*) AS total_rows,
    MIN(timestamp_utc) AS min_timestamp_utc,
    MAX(timestamp_utc) AS max_timestamp_utc
FROM entsoe_raw.total_load
GROUP BY source_file
ORDER BY source_file;

-- 10. Quick mart preview
-- Displays a small sample from the daily total_load mart view.
SELECT
    country_code,
    delivery_date,
    interval_minutes,
    records_count,
    avg_actual_load_mw,
    min_actual_load_mw,
    max_actual_load_mw,
    avg_forecast_load_mw,
    estimated_actual_load_mwh,
    estimated_forecast_load_mwh
FROM entsoe_mart.v_daily_total_load_summary
ORDER BY
    delivery_date,
    country_code,
    interval_minutes
LIMIT 20;
