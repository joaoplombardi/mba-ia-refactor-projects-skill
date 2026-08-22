"""Timezone-aware time helpers.

datetime.utcnow() is deprecated since Python 3.12 and returned a *naive*
datetime. The replacement returns an *aware* one, so the two cannot be compared:
every use in the project migrated together, and `ensure_aware` normalises rows
written by the previous naive version.
"""
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc)


def ensure_aware(value):
    """Attach UTC to a naive datetime so comparisons never raise TypeError."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
