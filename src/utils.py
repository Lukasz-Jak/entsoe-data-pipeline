import pandas as pd
from datetime import datetime, timezone
from typing import Union

def to_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def ensure_utc_index(df: pd.DataFrame, make_naive_for_storage: bool = True) -> pd.DataFrame:
    """
    Guarantees that the DataFrame index is a DatetimeIndex with UTC semantics.
    
    - If not a DatetimeIndex: converts via pd.to_datetime(..., utc=True)
    - If tz-aware: converts to UTC
    - If tz-naive: localizes to UTC
    - If make_naive_for_storage=True: strips timezone after ensuring UTC.
    - Sets index name to 'timestamp_utc'.
    """
    df = df.copy(deep=False)
    idx = df.index

    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.to_datetime(idx, utc=True)
    
    if idx.tz is not None:
        idx = idx.tz_convert("UTC")
    else:
        idx = idx.tz_localize("UTC")

    if make_naive_for_storage:
        idx = idx.tz_localize(None)

    df.index = idx
    df.index.name = "timestamp_utc"
    return df

def format_date_path(dt: datetime) -> str:
    """Format date for directory partitioning: YYYY/YYYY-MM."""
    return f"{dt.strftime('%Y')}/{dt.strftime('%Y-%m')}"
