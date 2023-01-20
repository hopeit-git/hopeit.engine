import uuid
from datetime import datetime, timezone

from hopeit.dataobjects import StreamEventParams

from . import MockNested, MockData, MockDataWithoutTs, MockDataWithAutoEventId

def test_data_event_params_extract_attr():
    now = datetime.now(tz=timezone.utc)
    obj = MockData(id='id1', value='value1', nested=MockNested(ts=now))
    assert StreamEventParams.extract_attr(obj, 'id') == 'id1'
    assert StreamEventParams.extract_attr(obj, 'value') == 'value1'
    assert StreamEventParams.extract_attr(obj, 'nested') == MockNested(ts=now)
    assert StreamEventParams.extract_attr(obj, 'nested.ts') == now


def test_data_event():
    now = datetime.now(tz=timezone.utc)
    obj = MockData(id='id1', value='value1', nested=MockNested(ts=now))
    assert obj.event_id() == 'id1'
    assert obj.event_ts() == now


def test_data_event_without_event_ts():
    obj = MockDataWithoutTs(id='id1', value='value1')
    assert obj.event_id() == 'id1'
    assert obj.event_ts() is None


def test_data_event_with_auto_event_id(monkeypatch):
    monkeypatch.setattr(uuid, 'uuid4', lambda: 'auto-id')
    obj = MockDataWithAutoEventId(value='value1')
    assert obj.event_id() == 'auto-id'
    assert obj.event_ts() is None
