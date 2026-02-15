from abc import ABC, abstractmethod
from datetime import datetime
from typing import Union

import pandas as pd

from src.api_client import EntsoeClient


class BaseDataset(ABC):
    """
    Abstract base class for ENTSO-E datasets.
    
    Canonical UTC Contract:
    - In-memory representation is always UTC.
    - fetch() must use explicit UTC-aware timestamps for API calls.
    - normalize() returns a DataFrame with a UTC-naive index (semantically UTC) 
      named 'timestamp_utc' for storage compatibility.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def fetch(self, client: EntsoeClient, start: Union[datetime, pd.Timestamp], end: Union[datetime, pd.Timestamp]) -> pd.DataFrame:
        """
        Fetch raw data from ENTSO-E.
         Datasets may accept naive datetime or pd.Timestamp inputs, but must enforce
        UTC-aware pd.Timestamp values before making API calls.
        """
        pass

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the dataset to the canonical representation:
        - Index name: 'timestamp_utc'
        - Index timezone: UTC-naive (but representing UTC)
        """
        pass

    def get_filename(self, start: Union[datetime, pd.Timestamp]) -> str:
        """
        Construct deterministic filename.
        Note: 'start' is treated as UTC for date-based pathing.
        """
        start_ts = pd.Timestamp(start)
        return f"{self.name}_{start_ts.strftime('%Y%m%d')}"
