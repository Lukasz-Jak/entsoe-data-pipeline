import os
import pandas as pd
import logging
from typing import List

logger = logging.getLogger(__name__)

class IOHandler:
    def __init__(self, base_path: str, formats: List[str]):
        self.base_path = base_path
        self.formats = [f.lower() for f in formats]

    def get_missing_formats(self, dataset_name: str, date_path: str, filename: str) -> List[str]:
        """Return a list of missing formats for the given dataset and date."""
        missing = []
        for fmt in self.formats:
            full_path = os.path.join(self.base_path, dataset_name, date_path, f"{filename}.{fmt}")
            if not os.path.exists(full_path):
                missing.append(fmt)
        return missing

    def write(self, df: pd.DataFrame, dataset_name: str, date_path: str, filename: str) -> None:
        """Write DataFrame to configured formats."""
        dir_path = os.path.join(self.base_path, dataset_name, date_path)
        os.makedirs(dir_path, exist_ok=True)

        for fmt in self.formats:
            full_path = os.path.join(dir_path, f"{filename}.{fmt}")
            if fmt == "csv":
                df.to_csv(full_path, index=True)
            elif fmt == "xlsx":
                df.to_excel(full_path, index=True)
            logger.info(f"Saved: {full_path}")
