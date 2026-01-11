import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset

class DayAheadPricesDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "day_ahead_prices"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        # Example for Poland (PL)
        return client.fetch_data(
            "query_day_ahead_prices",
            country_code="PL",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end)
        )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Centralized time normalization to UTC.
        Removes timezone info for Excel compatibility while keeping UTC semantics."""
        if isinstance(df, pd.Series):
            df = df.to_frame(name="price")
        
        # Ensure UTC and make naive for Excel support
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            
        df.index.name = "timestamp_utc"
        return df
