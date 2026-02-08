import logging
import pandas as pd
from datetime import datetime
from typing import List
from entsoe.exceptions import NoMatchingDataError
from src.api_client import EntsoeClient
from src.datasets.base import BaseDataset

logger = logging.getLogger(__name__)

class CrossborderPhysicalFlowsDataset(BaseDataset):
    """
    Dataset for Physical Cross-border Flows between Poland and other bidding zones.
    """
    
    def __init__(self, counterpart_areas: List[str]):
        normalized = [a.strip().upper() for a in (counterpart_areas or []) if a and a.strip()]
        self._counterpart_areas = sorted(set(normalized))

    @property
    def name(self) -> str:
        return "crossborder_physical_flows"

    def fetch(self, client: EntsoeClient, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Fetch physical cross-border flows for PL from/to configured counterpart areas.
        """
        if not self._counterpart_areas:
            logger.warning(
                f"No counterpart areas configured for {self.name}. "
                "Dataset will be skipped."
            )
            return pd.DataFrame()

        def _ensure_utc_ts(dt: datetime) -> pd.Timestamp:
            ts = pd.Timestamp(dt)
            if ts.tz is None:
                return ts.tz_localize("UTC")
            return ts.tz_convert("UTC")

        all_results = []
        
        # PL is always one side of the flow
        base_country = "PL"
        
        start_ts = _ensure_utc_ts(start)
        end_ts = _ensure_utc_ts(end)

        for area in self._counterpart_areas:
            # Check both directions: base -> area and area -> base
            directions = [
                (base_country, area),
                (area, base_country)
            ]
            
            for country_from, country_to in directions:
                try:
                    data = client.fetch_data(
                        "query_crossborder_flows",
                        country_code_from=country_from,
                        country_code_to=country_to,
                        start=start_ts,
                        end=end_ts
                    )
                    
                    if data is not None and not data.empty:
                        col_name = f"physical_flow_{country_from.lower()}_to_{country_to.lower()}"
                        
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
                except Exception:
                    logger.exception(
                        f"[{self.name}] Unexpected error for {start.date()} direction {country_from} -> {country_to} (start={start_ts}, end={end_ts})"
                    )
                    raise

        if not all_results:
            logger.warning(f"No data available for {self.name} on {start.date()} after checking all counterpart areas.")
            return pd.DataFrame()

        # Combine all pairs into a single DataFrame
        combined_df = pd.concat(all_results, axis=1, join="outer")
        return combined_df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize the combined physical flows data.
        """
        if df.empty:
            return df

        # Ensure UTC and make naive for storage compatibility
        idx = df.index
        if not isinstance(idx, pd.DatetimeIndex):
            df.index = pd.to_datetime(idx, utc=True).tz_localize(None)
        elif getattr(idx, "tz", None) is not None:
            df.index = idx.tz_convert("UTC").tz_localize(None)
        else:
            df.index = idx.tz_localize("UTC").tz_localize(None)
            
        df.index.name = "timestamp_utc"
        
        # Build deterministic pair-group column order
        base = "pl"
        # self._counterpart_areas is already sorted and uppercase
        areas = [a.lower() for a in self._counterpart_areas]
        
        ordered_cols = []
        for x in areas:
            preferred = [
                f"physical_flow_{base}_to_{x}",
                f"physical_flow_{x}_to_{base}",
            ]
            for col in preferred:
                if col in df.columns:
                    ordered_cols.append(col)
        
        # Append any remaining columns alphabetically
        remaining_cols = sorted([c for c in df.columns if c not in ordered_cols])
        
        df = df.reindex(columns=ordered_cols + remaining_cols)
        
        return df
