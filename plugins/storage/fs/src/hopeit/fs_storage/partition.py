"""
FS Storage plugin package module
"""

from datetime import datetime, timezone
from typing import Optional

from hopeit.dataobjects import DataObject


def get_partition_key(payload: Optional[DataObject], partition_dateformat: str) -> str:
    ts = _partition_timestamp(payload)
    return ts.strftime(partition_dateformat.strip("/")) + "/"


def _partition_timestamp(payload: Optional[DataObject]) -> datetime:
    ts = payload.event_ts() or datetime.now(tz=timezone.utc)  # type: ignore
    return ts.astimezone(timezone.utc)
