import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset

class TotalLoadDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "total_load"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch actual and forecast total load for Poland (PL)."""
        # Actual Load
        actual_load = client.fetch_data(
            "query_load",
            country_code="PL",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end)
        )
        
        # Forecast Load
        forecast_load = client.fetch_data(
            "query_load_forecast",
            country_code="PL",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end)
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
        # Ensure UTC and make naive for Excel support
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            
        df.index.name = "timestamp_utc"
        return df
