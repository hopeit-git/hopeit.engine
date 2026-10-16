from datetime import datetime, timezone, UTC

from hopeit.dataobjects import dataclass, dataobject
from hopeit.fs_storage import partition


@dataobject(event_id="object_id", event_ts="object_ts")
@dataclass
class TimedObject:
    object_id: str
    object_ts: datetime
    value: int


@dataobject
@dataclass
class UntimedObject:
    object_id: str
    value: int


def test_get_partition_timed_object():
    obj = TimedObject(
        "obj1",
        datetime.strptime("2020-05-01T00:00:00+00:00", "%Y-%m-%dT%H:%M:%S%z").astimezone(tz=UTC),
        value=1,
    )
    partition_key = partition.get_partition_key(obj, "%Y/%m/%d/%H")
    assert partition_key == "2020/05/01/00/"


class MockDatetime:
    @staticmethod
    def now(*args, **kwargs):
        return datetime.strptime("2021-06-02T01:00:00+00:00", "%Y-%m-%dT%H:%M:%S%z").astimezone(
            tz=UTC
        )


def test_get_partition_current_time(monkeypatch):
    monkeypatch.setattr(partition, "datetime", MockDatetime)
    obj = UntimedObject(object_id="obj2", value=2)
    partition_key = partition.get_partition_key(obj, "%Y/%m/%d/%H")
    assert partition_key == "2021/06/02/01/"
