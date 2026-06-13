CREATE SCHEMA IF NOT EXISTS entsoe_mart;

-- Identifies days with the highest intraday variability of actual electricity load.
-- load_spread_pct is the relative intraday spread compared with the average daily load.
CREATE OR REPLACE FUNCTION entsoe_mart.fn_get_high_load_variability_days(
    p_country_code TEXT,
    p_date_from DATE,
    p_date_to DATE,
    p_interval_minutes SMALLINT DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    country_code TEXT,
    delivery_date DATE,
    interval_minutes SMALLINT,
    records_count BIGINT,
    avg_actual_load_mw NUMERIC,
    min_actual_load_mw NUMERIC,
    max_actual_load_mw NUMERIC,
    load_spread_mw NUMERIC,
    load_spread_pct NUMERIC,
    estimated_actual_load_mwh NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH daily_load AS (
        SELECT
            tl.country_code AS country_code,
            tl.timestamp_utc::DATE AS delivery_date,
            tl.interval_minutes AS interval_minutes,
            COUNT(*) AS records_count,
            AVG(tl.actual_load_mw) AS avg_actual_load_mw,
            MIN(tl.actual_load_mw) AS min_actual_load_mw,
            MAX(tl.actual_load_mw) AS max_actual_load_mw,
            SUM(tl.actual_load_mw * tl.interval_minutes / 60.0) AS estimated_actual_load_mwh
        FROM entsoe_raw.total_load AS tl
        WHERE
            tl.country_code = p_country_code
            AND tl.timestamp_utc >= p_date_from
            AND tl.timestamp_utc < p_date_to + INTERVAL '1 day'
            AND (p_interval_minutes IS NULL OR tl.interval_minutes = p_interval_minutes)
            AND tl.actual_load_mw IS NOT NULL
        GROUP BY
            tl.country_code,
            tl.timestamp_utc::DATE,
            tl.interval_minutes
    )
    SELECT
        dl.country_code::TEXT AS country_code,
        dl.delivery_date,
        dl.interval_minutes,
        dl.records_count,
        ROUND(dl.avg_actual_load_mw::NUMERIC, 3) AS avg_actual_load_mw,
        ROUND(dl.min_actual_load_mw::NUMERIC, 3) AS min_actual_load_mw,
        ROUND(dl.max_actual_load_mw::NUMERIC, 3) AS max_actual_load_mw,
        ROUND((dl.max_actual_load_mw - dl.min_actual_load_mw)::NUMERIC, 3) AS load_spread_mw,
        ROUND(
            (
                (dl.max_actual_load_mw - dl.min_actual_load_mw)
                / NULLIF(dl.avg_actual_load_mw, 0)
                * 100.0
            )::NUMERIC,
            3
        ) AS load_spread_pct,
        ROUND(dl.estimated_actual_load_mwh::NUMERIC, 3) AS estimated_actual_load_mwh
    FROM daily_load AS dl
    ORDER BY
        load_spread_pct DESC NULLS LAST,
        load_spread_mw DESC,
        dl.delivery_date ASC
    LIMIT p_limit;
END;
$$;

-- Evaluates daily forecast accuracy by comparing forecasted load with actual load.
-- Positive forecast_bias_mw means the forecast was higher than actual load on average.
CREATE OR REPLACE FUNCTION entsoe_mart.fn_get_daily_load_forecast_error(
    p_country_code TEXT,
    p_date_from DATE,
    p_date_to DATE,
    p_interval_minutes SMALLINT DEFAULT NULL
)
RETURNS TABLE (
    country_code TEXT,
    delivery_date DATE,
    interval_minutes SMALLINT,
    records_count BIGINT,
    comparable_records_count BIGINT,
    avg_actual_load_mw NUMERIC,
    avg_forecast_load_mw NUMERIC,
    forecast_bias_mw NUMERIC,
    forecast_mae_mw NUMERIC,
    forecast_rmse_mw NUMERIC,
    max_abs_error_mw NUMERIC,
    mape_pct NUMERIC,
    bias_direction TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH filtered_load AS (
        SELECT
            tl.country_code,
            tl.timestamp_utc::DATE AS delivery_date,
            tl.interval_minutes,
            tl.actual_load_mw,
            tl.forecast_load_mw,
            CASE
                WHEN tl.actual_load_mw IS NOT NULL AND tl.forecast_load_mw IS NOT NULL
                    THEN tl.forecast_load_mw - tl.actual_load_mw
            END AS error_mw
        FROM entsoe_raw.total_load AS tl
        WHERE
            tl.country_code = p_country_code
            AND tl.timestamp_utc >= p_date_from
            AND tl.timestamp_utc < p_date_to + INTERVAL '1 day'
            AND (p_interval_minutes IS NULL OR tl.interval_minutes = p_interval_minutes)
    ),
    daily_error AS (
        SELECT
            fl.country_code,
            fl.delivery_date,
            fl.interval_minutes,
            COUNT(*) AS records_count,
            COUNT(*) FILTER (
                WHERE fl.actual_load_mw IS NOT NULL
                    AND fl.forecast_load_mw IS NOT NULL
            ) AS comparable_records_count,
            AVG(fl.actual_load_mw) AS avg_actual_load_mw,
            AVG(fl.forecast_load_mw) AS avg_forecast_load_mw,
            AVG(fl.error_mw) AS forecast_bias_mw,
            AVG(ABS(fl.error_mw)) AS forecast_mae_mw,
            SQRT(AVG(POWER(fl.error_mw, 2))) AS forecast_rmse_mw,
            MAX(ABS(fl.error_mw)) AS max_abs_error_mw,
            AVG(ABS(fl.error_mw / NULLIF(fl.actual_load_mw, 0))) * 100.0 AS mape_pct
        FROM filtered_load AS fl
        GROUP BY
            fl.country_code,
            fl.delivery_date,
            fl.interval_minutes
    )
    SELECT
        de.country_code::TEXT AS country_code,
        de.delivery_date,
        de.interval_minutes,
        de.records_count,
        de.comparable_records_count,
        ROUND(de.avg_actual_load_mw::NUMERIC, 3) AS avg_actual_load_mw,
        ROUND(de.avg_forecast_load_mw::NUMERIC, 3) AS avg_forecast_load_mw,
        ROUND(de.forecast_bias_mw::NUMERIC, 3) AS forecast_bias_mw,
        ROUND(de.forecast_mae_mw::NUMERIC, 3) AS forecast_mae_mw,
        ROUND(de.forecast_rmse_mw::NUMERIC, 3) AS forecast_rmse_mw,
        ROUND(de.max_abs_error_mw::NUMERIC, 3) AS max_abs_error_mw,
        ROUND(de.mape_pct::NUMERIC, 3) AS mape_pct,
        CASE
            WHEN de.comparable_records_count = 0 THEN 'not_available'
            WHEN de.forecast_bias_mw > 0 THEN 'overforecast'
            WHEN de.forecast_bias_mw < 0 THEN 'underforecast'
            ELSE 'neutral'
        END AS bias_direction
    FROM daily_error AS de
    ORDER BY
        de.delivery_date ASC,
        de.interval_minutes ASC;
END;
$$;

-- Example:
-- SELECT *
-- FROM entsoe_mart.fn_get_high_load_variability_days('PL', '2024-01-01', '2024-01-31', 60, 10);

-- Example:
-- SELECT *
-- FROM entsoe_mart.fn_get_daily_load_forecast_error('PL', '2024-01-01', '2024-01-31', 60);
