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

CREATE TABLE IF NOT EXISTS entsoe_raw.actual_generation (
    country_code TEXT NOT NULL DEFAULT 'PL',
    timestamp_utc TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    interval_minutes SMALLINT NOT NULL,
    production_type TEXT NOT NULL,
    measurement_type TEXT NOT NULL,
    source_column TEXT NOT NULL,
    value_mw NUMERIC(12, 3),
    source_file TEXT,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT pk_actual_generation
        PRIMARY KEY (
            country_code,
            timestamp_utc,
            interval_minutes,
            production_type,
            measurement_type
        ),

    CONSTRAINT chk_actual_generation_interval
        CHECK (interval_minutes > 0 AND 1440 % interval_minutes = 0),

    CONSTRAINT chk_actual_generation_non_negative
        CHECK (value_mw IS NULL OR value_mw >= 0)
);
