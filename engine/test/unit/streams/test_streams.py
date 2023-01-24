from datetime import datetime, timezone

import pytest

from pydantic import BaseModel

from hopeit.dataobjects import dataobject
from hopeit.streams import StreamManager


@dataobject(event_id='value', event_ts='ts')
class MockData:
    value: str
    ts: datetime


class MockInvalidDataEvent(BaseModel):
    value: str


def test_as_data_event():  # noqa: F811
    test_data = MockData(value="ok", ts=datetime.now(tz=timezone.utc))
    assert StreamManager.as_data_event(test_data) == test_data
    with pytest.raises(NotImplementedError):
        StreamManager.as_data_event(MockInvalidDataEvent(value="ok"))
