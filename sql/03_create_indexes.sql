CREATE INDEX IF NOT EXISTS idx_total_load_timestamp_utc
    ON entsoe_raw.total_load (timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_total_load_country_interval
    ON entsoe_raw.total_load (country_code, interval_minutes);
