import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset

class ActualGenerationDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "actual_generation"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch actual generation per production type for Poland (PL)."""
        return client.fetch_data(
            "query_generation",
            country_code="PL",
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
            psr_type=None  # Fetch full mix
        )

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the generation data:
        - Flatten MultiIndex columns to snake_case.
        - Ensure UTC semantics and timezone-naive index for Excel compatibility.
        - Set index name to 'timestamp_utc'.
        """
        # Handle MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            # entsoe-py typically returns columns like (Production Type, Actual Aggregated)
            # These are flattened into snake_case column names while preserving full structure
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
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            
        df.index.name = "timestamp_utc"
        return df
