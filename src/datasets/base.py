from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
from src.api_client import EntsoeClient

class BaseDataset(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        pass

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    def get_filename(self, start: datetime) -> str:
        """Construct deterministic filename."""
        return f"{self.name}_{start.strftime('%Y%m%d')}"
