import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset
from src.utils import to_utc, ensure_utc_index

class GenerationForecastWindSolarDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "generation_forecast_wind_solar"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch forecasted generation for wind and solar for Poland (PL)."""
        start_ts = pd.Timestamp(to_utc(start))
        if start_ts.tz is None:
            start_ts = start_ts.tz_localize("UTC")

        end_ts = pd.Timestamp(to_utc(end))
        if end_ts.tz is None:
            end_ts = end_ts.tz_localize("UTC")

        return client.fetch_data(
            "query_wind_and_solar_forecast",
            country_code="PL",
            start=start_ts,
            end=end_ts
        )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the generation forecast data:
        - Keep wind and solar forecasts as separate columns.
        - Flatten MultiIndex columns to clear snake_case.
        - Ensure UTC time semantics and remove timezone for Excel compatibility.
        - Name the index 'timestamp_utc'.
        """
        # Handle MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            new_cols = []
            for col in df.columns:
                # Filter out empty strings or None from parts, and flatten
                parts = [str(p).strip().lower().replace(" ", "_") for p in col if p and str(p).strip()]
                new_cols.append("_".join(parts))
            df.columns = new_cols
        else:
            # Simple column
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

        # Ensure UTC and make naive for Excel support
        return ensure_utc_index(df, make_naive_for_storage=True)
