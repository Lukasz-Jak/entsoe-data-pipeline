from datetime import datetime, timezone
from typing import Union

def to_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def format_date_path(dt: datetime) -> str:
    """Format date for directory partitioning: YYYY/YYYY-MM."""
    return f"{dt.strftime('%Y')}/{dt.strftime('%Y-%m')}"
