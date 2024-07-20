import dataclasses
from datetime import datetime, timezone
import uuid

from hopeit.dataobjects import StreamEventParams, copy_payload, dataobject
import pytest

from . import (
    MockNested,
    MockData,
    MockDataWithoutTs,
    MockDataWithAutoEventId,
    MockDataImmutable,
    MockDataUnsafe,
)


def test_data_event_params_extract_attr():
    now = datetime.now(tz=timezone.utc)
    obj = MockData("id1", "value1", MockNested(now))
    assert StreamEventParams.extract_attr(obj, "id") == "id1"
    assert StreamEventParams.extract_attr(obj, "value") == "value1"
    assert StreamEventParams.extract_attr(obj, "nested") == MockNested(now)
    assert StreamEventParams.extract_attr(obj, "nested.ts") == now


def test_data_event():
    now = datetime.now(tz=timezone.utc)
    obj = MockData("id1", "value1", MockNested(now))
    assert obj.event_id() == "id1"
    assert obj.event_ts() == now


def test_data_event_without_event_ts():
    obj = MockDataWithoutTs("id1", "value1")
    assert obj.event_id() == "id1"
    assert obj.event_ts() is None


def test_data_event_with_auto_event_id(monkeypatch):
    monkeypatch.setattr(uuid, "uuid4", lambda: "auto-id")
    obj = MockDataWithAutoEventId("value1")
    assert obj.event_id() == "auto-id"
    assert obj.event_ts() is None


def test_copy_mutable_dataobject():
    now = datetime.now(tz=timezone.utc)
    obj = MockData("id1", "value1", MockNested(now))
    new = copy_payload(obj)
    assert new == obj
    assert new is not obj


def test_copy_immutable_dataobject_should_return_same():
    now = datetime.now(tz=timezone.utc)
    obj = MockDataImmutable("id1", "value1", MockNested(now))
    new = copy_payload(obj)
    assert new == obj
    assert new is obj


def test_copy_unsafe_dataobject_should_return_same():
    now = datetime.now(tz=timezone.utc)
    obj = MockDataUnsafe("id1", "value1", MockNested(now))
    new = copy_payload(obj)
    assert new == obj
    assert new is obj


def test_copy_mutable_collection():
    test_dict = {"test": "value"}
    result = copy_payload(test_dict)
    assert result == test_dict and result is not test_dict

    test_list = ["test1", "test2"]
    result = copy_payload(test_list)
    assert result == test_list and result is not test_list

    test_set = {"test2", "test1"}
    result = copy_payload(test_set)
    assert result == test_set and result is not test_set


def test_copy_native_immutable_values_should_return_same():
    test_str, test_int, test_float, test_bool = "str", 123, 123.456, True
    assert copy_payload(test_str) is test_str
    assert copy_payload(test_int) is test_int
    assert copy_payload(test_float) is test_float
    assert copy_payload(test_bool) is test_bool


def test_check_dataclass_compatibility():
    with pytest.raises(TypeError):

        @dataobject
        @dataclasses.dataclass
        class MockNestedNonPydantic:
            """not a pydantic dataclass"""

            ts: datetime
