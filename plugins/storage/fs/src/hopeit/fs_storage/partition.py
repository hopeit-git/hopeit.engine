"""
FS Storage plugin package module
"""

from datetime import datetime, timezone

from hopeit.dataobjects import DataObject


def get_file_partition_key(partition_dateformat: str) -> str:
    ts = datetime.now(tz=timezone.utc)
    return ts.astimezone(timezone.utc).strftime(partition_dateformat.strip("/")) + "/"


def get_partition_key(payload: DataObject, partition_dateformat: str) -> str:
    ts = payload.event_ts() or datetime.now(tz=timezone.utc)  # type: ignore
    return ts.astimezone(timezone.utc).strftime(partition_dateformat.strip("/")) + "/"
