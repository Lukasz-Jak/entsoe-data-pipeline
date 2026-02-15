import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset
from src.utils import to_utc, ensure_utc_index

class GenerationForecastDayAheadDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "generation_forecast_day_ahead"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch day-ahead generation forecast for Poland (PL)."""
        start_ts = pd.Timestamp(to_utc(start))
        if start_ts.tz is None:
            start_ts = start_ts.tz_localize("UTC")

        end_ts = pd.Timestamp(to_utc(end))
        if end_ts.tz is None:
            end_ts = end_ts.tz_localize("UTC")

        return client.fetch_data(
            "query_generation_forecast",
            country_code="PL",
            start=start_ts,
            end=end_ts
        )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the generation forecast data:
        - Convert Series to DataFrame if necessary.
        - Flatten MultiIndex columns to snake_case.
        - Ensure UTC semantics and timezone-naive index for Excel compatibility.
        - Set index name to 'timestamp_utc'.
        """
        # Convert Series to DataFrame if necessary
        if isinstance(df, pd.Series):
            df = df.to_frame(name="generation_forecast")

        # Handle MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            new_cols = []
            for col in df.columns:
                # Filter out empty strings or None from parts
                parts = [str(p).strip().lower().replace(" ", "_") for p in col if p and str(p).strip()]
                new_cols.append("_".join(parts))
            df.columns = new_cols
        else:
            # Simple index
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

        # Ensure UTC and make naive for Excel support
        return ensure_utc_index(df, make_naive_for_storage=True)
