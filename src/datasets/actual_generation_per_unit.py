import logging
import pandas as pd
from datetime import datetime
from entsoe.exceptions import NoMatchingDataError
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset

logger = logging.getLogger(__name__)

class ActualGenerationPerUnitDataset(BaseDataset):
    @property
    def name(self) -> str:
        return "actual_generation_per_unit"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Fetch actual generation per generation unit for Poland (PL).
        Handles cases where no data is available by logging a warning and returning an empty DataFrame.
        """
        try:
            df = client.fetch_data(
                "query_generation_per_plant",
                country_code="PL",
                start=pd.Timestamp(start),
                end=pd.Timestamp(end),
                psr_type=None,
                include_eic=False
            )
        except NoMatchingDataError:
            logger.warning(
                f"No data published yet for {self.name} on {start.date()} (ENTSO-E reporting delay (NoMatchingDataError)). "
                f"Dataset will be skipped for this date."
            )
            return pd.DataFrame()
        
        if df.empty:
            logger.warning(
                f"No data available for {self.name} on {start.date()}. "
                "This dataset will be skipped for this date."
            )
        
        return df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the generation per unit data:
        - Flatten MultiIndex columns to snake_case.
        - Ensure UTC semantics and timezone-naive index for Excel compatibility.
        - Set index name to 'timestamp_utc'.
        """
        if df.empty:
            return df

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
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            
        df.index.name = "timestamp_utc"
        return df
