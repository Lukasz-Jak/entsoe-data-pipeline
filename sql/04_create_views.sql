CREATE SCHEMA IF NOT EXISTS entsoe_mart;

CREATE OR REPLACE VIEW entsoe_mart.v_daily_total_load_summary AS
SELECT
    country_code,
    timestamp_utc::DATE AS delivery_date,
    interval_minutes,
    COUNT(*) AS records_count,
    AVG(actual_load_mw) AS avg_actual_load_mw,
    MIN(actual_load_mw) AS min_actual_load_mw,
    MAX(actual_load_mw) AS max_actual_load_mw,
    AVG(forecast_load_mw) AS avg_forecast_load_mw,
    SUM(actual_load_mw * interval_minutes / 60.0) AS estimated_actual_load_mwh,
    SUM(forecast_load_mw * interval_minutes / 60.0) AS estimated_forecast_load_mwh
FROM entsoe_raw.total_load
GROUP BY
    country_code,
    timestamp_utc::DATE,
    interval_minutes;
