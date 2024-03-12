"""
FS Storage plugin package module
"""

from datetime import datetime, timezone
from typing import Optional

from hopeit.dataobjects import DataObject


def get_partition_key(payload: Optional[DataObject], partition_dateformat: str) -> str:
    if payload and hasattr(payload, "event_ts"):
        ts = payload.event_ts() or datetime.now(tz=timezone.utc)
    else:
        ts = datetime.now(tz=timezone.utc)
    return ts.astimezone(timezone.utc).strftime(partition_dateformat.strip("/")) + "/"
