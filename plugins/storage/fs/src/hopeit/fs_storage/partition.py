"""
FS Storage plugin package module
"""
from datetime import datetime, timezone

from hopeit.dataobjects import DataObject


def get_partition_key(payload: DataObject, partition_dateformat: str) -> str:
    prefix = ""
    event_partitions = payload.event_partition_keys()
    print()
    print("**** event_partitions", event_partitions)
    if event_partitions is not None:
        prefix = "/".join(event_partitions) + "/"
    print("**** prefix", prefix)
    print()
    ts = _partition_timestamp(payload)
    return prefix + ts.strftime(partition_dateformat.strip('/')) + '/'


def _partition_timestamp(payload: DataObject) -> datetime:
    ts = payload.event_ts() or datetime.now(tz=timezone.utc)  # type: ignore
    return ts.astimezone(timezone.utc)
