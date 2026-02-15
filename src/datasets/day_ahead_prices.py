import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset
from src.utils import to_utc, ensure_utc_index

class DayAheadPricesDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "day_ahead_prices"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        # Example for Poland (PL)
        start_ts = pd.Timestamp(to_utc(start))
        if start_ts.tz is None:
            start_ts = start_ts.tz_localize("UTC")

        end_ts = pd.Timestamp(to_utc(end))
        if end_ts.tz is None:
            end_ts = end_ts.tz_localize("UTC")

        return client.fetch_data(
            "query_day_ahead_prices",
            country_code="PL",
            start=start_ts,
            end=end_ts
        )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Centralized time normalization to UTC.
        Removes timezone info for Excel compatibility while keeping UTC semantics."""
        if isinstance(df, pd.Series):
            df = df.to_frame(name="price")
        
        # Ensure UTC and make naive for Excel support
        return ensure_utc_index(df, make_naive_for_storage=True)
