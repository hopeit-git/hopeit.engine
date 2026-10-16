"""
FS Storage plugin package module
"""

from datetime import UTC, datetime

from hopeit.dataobjects import DataObject


def get_file_partition_key(partition_dt: datetime | None, partition_dateformat: str) -> str:
    ts = partition_dt or datetime.now(tz=UTC)
    return ts.astimezone(UTC).strftime(partition_dateformat.strip("/")) + "/"


def get_partition_key(payload: DataObject, partition_dateformat: str) -> str:
    ts = payload.event_ts() or datetime.now(tz=UTC)  # type: ignore
    return ts.astimezone(UTC).strftime(partition_dateformat.strip("/")) + "/"
