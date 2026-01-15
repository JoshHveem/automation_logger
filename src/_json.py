from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def jsonable(value: Any) -> Any:
    """Make values JSON-serializable, with forgiving fallbacks."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool, list, dict)):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)
