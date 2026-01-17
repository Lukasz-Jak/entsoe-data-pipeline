import logging
import time
from typing import Any, Optional
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError
import pandas as pd

logger = logging.getLogger(__name__)

class EntsoeClient:
    def __init__(self, api_key: str, retry_count: int = 5, backoff_factor: float = 1.0):
        self.client = EntsoePandasClient(api_key=api_key)
        self.retry_count = retry_count
        self.backoff_factor = backoff_factor

    def fetch_data(self, fetch_func_name: str, **kwargs: Any) -> pd.DataFrame:
        """Fetch data with exponential backoff retry logic."""
        try:
            fetch_func = getattr(self.client, fetch_func_name)
        except AttributeError:
            logger.exception(f"Unknown fetch function: {fetch_func_name}")
            raise

        attempt = 0
        while attempt < self.retry_count:
            try:
                return fetch_func(**kwargs)
            except NoMatchingDataError:
                # Do not retry on NoMatchingDataError - it's a valid "no data" response
                raise
            except Exception as e:
                attempt += 1
                if attempt == self.retry_count:
                    logger.exception(f"Failed to fetch data after {self.retry_count} attempts")
                    raise
                
                sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
        
        raise RuntimeError("Unreachable code in fetch_data")
