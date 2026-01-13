"""Timezone-aware UTC timestamp utilities."""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current time as timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: Optional[datetime] = None) -> datetime:
    """
    Ensure datetime is timezone-aware and in UTC.
    
    Args:
        dt: Optional datetime. If None, returns current UTC time.
            If naive, assumes UTC. If timezone-aware, converts to UTC.
    
    Returns:
        Timezone-aware UTC datetime.
    """
    if dt is None:
        return utc_now()
    
    if dt.tzinfo is None:
        # Naive datetime, assume UTC
        return dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC if not already
    return dt.astimezone(timezone.utc)

