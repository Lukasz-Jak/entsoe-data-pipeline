import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset
from src.utils import to_utc, ensure_utc_index

class TotalLoadDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "total_load"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch actual and forecast total load for Poland (PL)."""
        start_ts = pd.Timestamp(to_utc(start))
        if start_ts.tz is None:
            start_ts = start_ts.tz_localize("UTC")

        end_ts = pd.Timestamp(to_utc(end))
        if end_ts.tz is None:
            end_ts = end_ts.tz_localize("UTC")

        # Actual Load
        actual_load = client.fetch_data(
            "query_load",
            country_code="PL",
            start=start_ts,
            end=end_ts
        )
        
        # Forecast Load
        forecast_load = client.fetch_data(
            "query_load_forecast",
            country_code="PL",
            start=start_ts,
            end=end_ts
        )

        # Merge actual and forecast
        # entsoe-py usually returns Series or DataFrame with TimeIndex
        if isinstance(actual_load, pd.Series):
            actual_load = actual_load.to_frame(name="actual_load")
        else:
            # If it's a DataFrame, it might have multiple columns depending on the query
            # but query_load for a single country usually returns a single column or MultiIndex
            actual_load = actual_load.rename(columns={actual_load.columns[0]: "actual_load"})

        if isinstance(forecast_load, pd.Series):
            forecast_load = forecast_load.to_frame(name="forecast_load")
        else:
            forecast_load = forecast_load.rename(columns={forecast_load.columns[0]: "forecast_load"})

        # Combine data
        df = pd.concat([actual_load, forecast_load], axis=1)
        return df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Centralized time normalization to UTC.
        Removes timezone info for Excel compatibility while keeping UTC semantics."""
        return ensure_utc_index(df, make_naive_for_storage=True)
