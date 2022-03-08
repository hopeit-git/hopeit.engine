from datetime import datetime, timezone

import pytest

from hopeit.dataobjects import dataobject, dataclass
from hopeit.streams import StreamManager


@dataobject(event_id='value', event_ts='ts')
@dataclass
class MockData:
    value: str
    ts: datetime


@dataclass
class MockInvalidDataEvent:
    value: str


def test_as_data_event():  # noqa: F811
    test_data = MockData("ok", datetime.now(tz=timezone.utc))
    assert StreamManager.as_data_event(test_data) == test_data
    with pytest.raises(NotImplementedError):
        StreamManager.as_data_event(MockInvalidDataEvent("ok"))
