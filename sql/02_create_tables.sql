CREATE TABLE IF NOT EXISTS entsoe_raw.total_load (
    country_code TEXT NOT NULL DEFAULT 'PL',
    timestamp_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    interval_minutes SMALLINT NOT NULL,
    actual_load_mw NUMERIC(12, 3),
    forecast_load_mw NUMERIC(12, 3),
    source_file TEXT,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_total_load
        PRIMARY KEY (country_code, timestamp_utc, interval_minutes),

    CONSTRAINT chk_total_load_interval
        CHECK (interval_minutes IN (15, 60)),

    CONSTRAINT chk_total_load_non_negative
        CHECK (
            (actual_load_mw IS NULL OR actual_load_mw >= 0)
            AND
            (forecast_load_mw IS NULL OR forecast_load_mw >= 0)
        )
);
