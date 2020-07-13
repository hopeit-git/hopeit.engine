import pytest
import json
import uuid
from datetime import datetime, timezone
import dataclasses

from hopeit.dataobjects import StreamEventParams, dataobject, copy_payload, dataclass, field
from hopeit.dataobjects.jsonify import Json


@dataobject
@dataclass
class MockNested:
    ts: datetime


@dataobject(event_id='id', event_ts='nested.ts')
@dataclass
class MockData:
    id: str
    value: str
    nested: MockNested


@dataobject(event_id='id')
@dataclass
class MockDataWithoutTs:
    id: str
    value: str


@dataobject
@dataclass
class MockDataWithAutoEventId:
    value: str


@dataobject
@dataclass(frozen=True)
class MockDataImmutable:
    id: str
    value: str
    nested: MockNested


@dataobject(unsafe=True)
@dataclass
class MockDataUnsafe:
    id: str
    value: str
    nested: MockNested


@dataobject
@dataclass
class MockDataValidate:
    id: str
    value: int


@dataobject(validate=False)
@dataclass
class MockDataDoNotValidate:
    id: str
    value: int


def test_data_event_params_extract_attr():
    now = datetime.now()
    obj = MockData('id1', 'value1', MockNested(now))
    assert StreamEventParams.extract_attr(obj, 'id') == 'id1'
    assert StreamEventParams.extract_attr(obj, 'value') == 'value1'
    assert StreamEventParams.extract_attr(obj, 'nested') == MockNested(now)
    assert StreamEventParams.extract_attr(obj, 'nested.ts') == now


def test_data_event():
    now = datetime.now()
    obj = MockData('id1', 'value1', MockNested(now))
    assert obj.event_id() == 'id1'
    assert obj.event_ts() == now


def test_data_event_without_event_ts():
    obj = MockDataWithoutTs('id1', 'value1')
    assert obj.event_id() == 'id1'
    assert obj.event_ts() is None


def test_data_event_with_auto_event_id(monkeypatch):
    monkeypatch.setattr(uuid, 'uuid4', lambda: 'auto-id')
    obj = MockDataWithAutoEventId('value1')
    assert obj.event_id() == 'auto-id'
    assert obj.event_ts() is None


def test_copy_mutable_dataobject():
    now = datetime.now()
    obj = MockData('id1', 'value1', MockNested(now))
    new = copy_payload(obj)
    assert new == obj
    assert new is not obj


def test_copy_immutable_dataobject_should_return_same():
    now = datetime.now()
    obj = MockDataImmutable('id1', 'value1', MockNested(now))
    new = copy_payload(obj)
    assert new == obj
    assert new is obj


def test_copy_unsafe_dataobject_should_return_same():
    now = datetime.now()
    obj = MockDataUnsafe('id1', 'value1', MockNested(now))
    new = copy_payload(obj)
    assert new == obj
    assert new is obj


def test_copy_mutable_collection():
    test_dict = {'test': 'value'}
    result = copy_payload(test_dict)
    assert result == test_dict and result is not test_dict

    test_list = ['test1', 'test2']
    result = copy_payload(test_list)
    assert result == test_list and result is not test_list

    test_set = {'test2', 'test1'}
    result = copy_payload(test_set)
    assert result == test_set and result is not test_set


def test_copy_native_immutable_values_should_return_same():
    test_str, test_int, test_float, test_bool = "str", 123, 123.456, True
    assert copy_payload(test_str) is test_str
    assert copy_payload(test_int) is test_int
    assert copy_payload(test_float) is test_float
    assert copy_payload(test_bool) is test_bool


def test_to_json_python_types():
    assert Json.to_json('str', key=None) == '"str"'
    assert Json.to_json(123, key=None) == '123'
    assert Json.to_json(123.45, key=None) == '123.45'
    assert Json.to_json(True, key=None) == 'true'
    assert Json.to_json('str', key='test') == '{"test": "str"}'
    assert Json.to_json(123, key='test') == '{"test": 123}'
    assert Json.to_json(123.45, key='test') == '{"test": 123.45}'
    assert Json.to_json(True, key='test') == '{"test": true}'
    assert Json.to_json({'test': 'dict'}) == '{"test": "dict"}'
    assert set(json.loads(Json.to_json({'test2', 'test1'}))) == {"test1", "test2"}
    assert Json.to_json(['test1', 'test2']) == '["test1", "test2"]'


def test_to_json_list_dataobject():
    assert json.loads(Json.to_json([
        MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    ])) == [{"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
            {"id": "2", "value": "ok-2", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}]


def test_to_json_dict_dataobject():
    assert json.loads(Json.to_json({
        'item1': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        'item2': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    })) == {"item1": {"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
            "item2": {"id": "2", "value": "ok-2", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}}


def test_to_json_list_mixed():
    assert json.loads(Json.to_json([
        {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        },
        {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        }
    ])) == [{'data': {'id': '1',
                      'nested': {'ts': '1970-01-01T00:00:00+00:00'},
                      'value': 'ok-1'},
             'item': 1},
            {'data': {'id': '2',
                      'nested': {'ts': '1970-01-01T00:00:00+00:00'},
                      'value': 'ok-2'},
             'item': 2}]


def test_to_json_dict_mixed():
    assert json.loads(Json.to_json({
        "item1": {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        },
        "item2": {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        }
    })) == {'item1': {'data': {'id': '1',
                               'nested': {'ts': '1970-01-01T00:00:00+00:00'},
                               'value': 'ok-1'},
                      'item': 1},
            'item2': {'data': {'id': '2',
                               'nested': {'ts': '1970-01-01T00:00:00+00:00'},
                               'value': 'ok-2'},
                      'item': 2}}


def test_to_json_dataobject():
    assert Json.to_json(MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0, tz=timezone.utc)
        )
    )) == '{"id": "test", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}'


def test_from_json_python_types():
    assert Json.from_json('{"value": "str"}', str) == "str"
    assert Json.from_json('{"value": 123}', int) == int(123)
    assert Json.from_json('{"value": 123.45}', float) == float(123.45)
    assert Json.from_json('{"value": true}', bool) is True
    assert Json.from_json('{"custom": "str"}', str, key='custom') == "str"
    assert Json.from_json('{"test": "dict"}', dict) == {'test': 'dict'}
    assert Json.from_json('["test1", "test2"]', set) == {'test2', 'test1'}
    assert Json.from_json('["test1", "test2"]', list) == ['test1', 'test2']


def text_from_json_dataobject():
    assert Json.from_json(
        '{"id": "test", "value": "ok", "nested": {"ts": 0.0}}', MockData
    ) == MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0.0)
        )
    )


def test_from_json_dataobject_validate():
    data = '{"id": "test", "value": "not-ok"}'
    with pytest.raises(ValueError):
        Json.from_json(data, MockDataValidate)


def test_from_json_dataobject_do_not_validate():
    data = '{"id": "test", "value": "not-ok"}'
    assert Json.from_json(data, MockDataDoNotValidate) \
        == MockDataDoNotValidate(id='test', value='not-ok')  # type: ignore


def test_to_json_dataobject_validate():
    data = MockDataValidate(id='test', value='not-ok')  # type: ignore
    with pytest.raises(ValueError):
        Json.to_json(data)


def test_to_json_dataobject_do_not_validate():
    data = MockDataDoNotValidate(id='test', value='not-ok')  # type: ignore
    assert Json.to_json(data) == '{"id": "test", "value": "not-ok"}'


def test_from_json_invalid_types():
    with pytest.raises(ValueError):
        Json.from_json('{"id": "1", "value": "ok-1", "nested": {"ts": "INVALID DATE"}}', MockData)

    with pytest.raises(ValueError):
        Json.from_json('{"id": 42, "value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData)


def test_from_json_missing_fields():
    with pytest.raises(ValueError):
        Json.from_json('{"id": "1", "value": "ok-1", "nested": {}', MockData)

    with pytest.raises(ValueError):
        Json.from_json('{"value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData)


def test_from_json_malformed():
    with pytest.raises(ValueError):
        Json.from_json(
            '{"item1": {"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}', MockData)

    with pytest.raises(ValueError):
        Json.from_json('BAD STRING', MockData)


def test_to_json_invalid_types():
    with pytest.raises(ValueError):
        Json.to_json(
            MockData(id=42, value='ok-value', nested=MockNested(ts=datetime.now(tz=timezone.utc))))  # type: ignore

    with pytest.raises(ValueError):
        Json.to_json(MockData(id='1', value='ok-value', nested=MockNested(ts="NOT A DATETIME")))  # type: ignore


def test_dataclass_field_wrapper():
    def assert_eq_field(a, b):
        assert a.metadata == b.metadata
        assert a.default == b.default
        assert a.default_factory == b.default_factory
        assert a.name == b.name
        assert a.init == b.init
        assert a.hash == b.hash
        assert a.repr == b.repr
    
    assert_eq_field(field("Foo"), dataclasses.field(metadata={"description": "Foo"}))
    assert_eq_field(field("Foo", default_factory=dict),
         dataclasses.field(metadata={"description": "Foo"}, default_factory=dict))
