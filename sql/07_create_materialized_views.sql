CREATE SCHEMA IF NOT EXISTS entsoe_mart;

DROP MATERIALIZED VIEW IF EXISTS entsoe_mart.mv_monthly_total_load_summary;

CREATE MATERIALIZED VIEW entsoe_mart.mv_monthly_total_load_summary AS
SELECT
    country_code,
    date_trunc('month', timestamp_utc)::DATE AS month_start,
    interval_minutes,
    COUNT(*) AS records_count,
    MIN(timestamp_utc) AS first_timestamp_utc,
    MAX(timestamp_utc) AS last_timestamp_utc,
    AVG(actual_load_mw) AS avg_actual_load_mw,
    MIN(actual_load_mw) AS min_actual_load_mw,
    MAX(actual_load_mw) AS max_actual_load_mw,
    SUM(actual_load_mw * interval_minutes / 60.0) AS estimated_actual_load_mwh,
    AVG(forecast_load_mw) AS avg_forecast_load_mw,
    AVG(
        CASE
            WHEN actual_load_mw IS NOT NULL AND forecast_load_mw IS NOT NULL
                THEN ABS(forecast_load_mw - actual_load_mw)
        END
    ) AS forecast_mae_mw,
    -- Positive forecast bias means the forecast was higher than actual load on average.
    AVG(
        CASE
            WHEN actual_load_mw IS NOT NULL AND forecast_load_mw IS NOT NULL
                THEN forecast_load_mw - actual_load_mw
        END
    ) AS forecast_bias_mw
FROM entsoe_raw.total_load
GROUP BY
    country_code,
    date_trunc('month', timestamp_utc)::DATE,
    interval_minutes
WITH DATA;

CREATE UNIQUE INDEX idx_mv_monthly_total_load_summary_unique
    ON entsoe_mart.mv_monthly_total_load_summary (
        country_code,
        month_start,
        interval_minutes
    );

CREATE INDEX idx_mv_monthly_total_load_summary_country_month
    ON entsoe_mart.mv_monthly_total_load_summary (
        country_code,
        month_start
    );

DROP MATERIALIZED VIEW IF EXISTS entsoe_mart.mv_monthly_generation_mix_by_type;

CREATE MATERIALIZED VIEW entsoe_mart.mv_monthly_generation_mix_by_type AS
WITH monthly_generation AS (
    SELECT
        country_code,
        date_trunc('month', timestamp_utc)::DATE AS month_start,
        interval_minutes,
        production_type,
        measurement_type,
        COUNT(*) AS records_count,
        MIN(timestamp_utc) AS first_timestamp_utc,
        MAX(timestamp_utc) AS last_timestamp_utc,
        SUM(value_mw * interval_minutes / 60.0) AS estimated_generation_mwh,
        AVG(value_mw) AS avg_generation_mw,
        MAX(value_mw) AS max_generation_mw
    FROM entsoe_raw.actual_generation
    GROUP BY
        country_code,
        date_trunc('month', timestamp_utc)::DATE,
        interval_minutes,
        production_type,
        measurement_type
)
SELECT
    country_code,
    month_start,
    interval_minutes,
    production_type,
    measurement_type,
    records_count,
    first_timestamp_utc,
    last_timestamp_utc,
    estimated_generation_mwh,
    avg_generation_mw,
    max_generation_mw,
    estimated_generation_mwh
        / NULLIF(
            SUM(estimated_generation_mwh) OVER (
                PARTITION BY
                    country_code,
                    month_start,
                    interval_minutes,
                    measurement_type
            ),
            0
        )
        * 100.0 AS share_in_month_pct,
    RANK() OVER (
        PARTITION BY
            country_code,
            month_start,
            interval_minutes,
            measurement_type
        ORDER BY estimated_generation_mwh DESC NULLS LAST
    ) AS rank_in_month
FROM monthly_generation
WITH DATA;

CREATE UNIQUE INDEX idx_mv_monthly_generation_mix_by_type_unique
    ON entsoe_mart.mv_monthly_generation_mix_by_type (
        country_code,
        month_start,
        interval_minutes,
        production_type,
        measurement_type
    );

CREATE INDEX idx_mv_monthly_generation_mix_by_type_country_month
    ON entsoe_mart.mv_monthly_generation_mix_by_type (
        country_code,
        month_start
    );

CREATE INDEX idx_mv_monthly_generation_mix_by_type_production_type
    ON entsoe_mart.mv_monthly_generation_mix_by_type (
        production_type
    );

-- Refresh examples:
-- REFRESH MATERIALIZED VIEW entsoe_mart.mv_monthly_total_load_summary;
-- REFRESH MATERIALIZED VIEW entsoe_mart.mv_monthly_generation_mix_by_type;

-- Concurrent refresh examples require the unique indexes defined above:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY entsoe_mart.mv_monthly_total_load_summary;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY entsoe_mart.mv_monthly_generation_mix_by_type;
