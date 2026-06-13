CREATE INDEX IF NOT EXISTS idx_total_load_timestamp_utc
    ON entsoe_raw.total_load (timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_total_load_country_interval
    ON entsoe_raw.total_load (country_code, interval_minutes);

CREATE INDEX IF NOT EXISTS idx_actual_generation_timestamp_utc
    ON entsoe_raw.actual_generation (timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_actual_generation_country_type_measurement_timestamp
    ON entsoe_raw.actual_generation (
        country_code,
        production_type,
        measurement_type,
        timestamp_utc
    );

CREATE INDEX IF NOT EXISTS idx_actual_generation_country_interval
    ON entsoe_raw.actual_generation (country_code, interval_minutes);
