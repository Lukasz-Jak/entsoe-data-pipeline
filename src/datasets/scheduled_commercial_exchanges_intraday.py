import logging
import pandas as pd
from datetime import datetime
from typing import List
from entsoe.exceptions import NoMatchingDataError
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset

logger = logging.getLogger(__name__)

class ScheduledCommercialExchangesIntradayDataset(BaseDataset):
    """
    Dataset for Scheduled Commercial Exchanges (Intraday) between Poland and other bidding zones.
    """
    
    def __init__(self, counterpart_areas: List[str]):
        self._counterpart_areas = [area.strip().upper() for area in counterpart_areas] if counterpart_areas else []

    @property
    def name(self) -> str:
        return "scheduled_commercial_exchanges_intraday"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Fetch intraday scheduled commercial exchanges for PL from/to configured counterpart areas.
        """
        if not self._counterpart_areas:
            logger.warning(
                f"No counterpart areas configured for {self.name}. "
                "Dataset will be skipped."
            )
            return pd.DataFrame()

        all_results = []
        
        # PL is always one side of the exchange
        base_country = "PL"
        
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        for area in self._counterpart_areas:
            # Check both directions: base -> area and area -> base
            directions = [
                (base_country, area),
                (area, base_country)
            ]
            
            for country_from, country_to in directions:
                try:
                    data = client.fetch_data(
                        "query_scheduled_exchanges",
                        country_code_from=country_from,
                        country_code_to=country_to,
                        start=start_ts,
                        end=end_ts,
                        dayahead=False
                    )
                    
                    if data is not None and not data.empty:
                        col_name = f"scheduled_exchange_{country_from.lower()}_to_{country_to.lower()}"
                        
                        if isinstance(data, pd.Series):
                            df_pair = data.to_frame(name=col_name)
                        elif isinstance(data, pd.DataFrame):
                            if len(data.columns) == 1:
                                df_pair = data.copy()
                                df_pair.columns = [col_name]
                            else:
                                logger.warning(
                                    f"[{self.name}] Unexpected multi-column response for {country_from} -> {country_to}. "
                                    f"Columns: {list(data.columns)}. Skipping this direction."
                                )
                                continue
                        else:
                            continue
                        
                        all_results.append(df_pair)
                        
                except NoMatchingDataError:
                    logger.warning(
                        f"[{self.name}] No data found for {start.date()} direction {country_from} -> {country_to}."
                    )
                except Exception as e:
                    logger.error(
                        f"[{self.name}] Error fetching data for {start.date()} direction {country_from} -> {country_to}: {e}"
                    )

        if not all_results:
            logger.warning(f"No data available for {self.name} on {start.date()} after checking all counterpart areas.")
            return pd.DataFrame()

        # Combine all pairs into a single DataFrame
        combined_df = pd.concat(all_results, axis=1, join="outer")
        return combined_df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the combined exchanges data.
        """
        if df.empty:
            return df

        # Ensure UTC and make naive for storage compatibility
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
            
        df.index.name = "timestamp_utc"
        
        # Sort columns deterministically
        df = df.reindex(sorted(df.columns), axis=1)
        
        return df
