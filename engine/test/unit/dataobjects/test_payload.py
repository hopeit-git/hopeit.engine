from typing import Dict, List
from pydantic import ValidationError
import pytest
import json
from datetime import datetime, timezone

from hopeit.dataobjects.payload import Payload

from . import MockNested, MockData, MockDataValidate, MockDataNullable


def test_to_json_python_types():
    assert Payload.to_json('str', key='test') == '{"test":"str"}'
    assert Payload.to_json(123, key='test') == '{"test":123}'
    assert Payload.to_json(123.45, key='test') == '{"test":123.45}'
    assert Payload.to_json(True, key='test') == '{"test":true}'
    assert Payload.to_json({'test': 'dict'}) == '{"test":"dict"}'
    assert set(json.loads(Payload.to_json({'test2', 'test1'}))) == {"test1","test2"}
    assert Payload.to_json(['test1', 'test2']) == '["test1","test2"]'


def test_to_obj_python_types():
    assert Payload.to_obj('str', key='test') == {"test": "str"}
    assert Payload.to_obj(123, key='test') == {"test": 123}
    assert Payload.to_obj(123.45, key='test') == {"test": 123.45}
    assert Payload.to_obj(True, key='test') == {"test": True}
    assert Payload.to_obj({'test': 'dict'}) == {"test": "dict"}
    assert Payload.to_obj({'test2', 'test1'}) == {"test1", "test2"}
    assert Payload.to_obj(['test2', 'test1']) == ["test2", "test1"]


def test_to_json_list_dataobject():
    assert json.loads(Payload.to_json([
        MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    ])) == [{"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00Z"}},
            {"id": "2", "value": "ok-2", "nested": {"ts": "1970-01-01T00:00:00Z"}}]


def test_to_obj_list_dataobject():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert Payload.to_obj([
        MockData(id='1', value='ok-1', nested=MockNested(ts=ts)),
        MockData(id='2', value='ok-2', nested=MockNested(ts=ts)),
    ]) == [{"id": "1", "value": "ok-1", "nested": {"ts": ts}},
           {"id": "2", "value": "ok-2", "nested": {"ts": ts}}]


def test_to_json_dict_dataobject():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert Payload.to_json({
        'item1': MockData(id='1', value='ok-1', nested=MockNested(ts=ts)),
        'item2': MockData(id='2', value='ok-2', nested=MockNested(ts=ts)),
    }) == (
        '{"item1":{"id":"1","value":"ok-1","nested":{"ts":"1970-01-01T00:00:00Z"}},'
        '"item2":{"id":"2","value":"ok-2","nested":{"ts":"1970-01-01T00:00:00Z"}}}'
    )


def test_to_obj_dict_dataobject():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert Payload.to_obj({
        'item1': MockData(id='1', value='ok-1', nested=MockNested(ts=ts)),
        'item2': MockData(id='2', value='ok-2', nested=MockNested(ts=ts)),
    }) == {"item1": {"id": "1", "value": "ok-1", "nested": {"ts": ts}},
           "item2": {"id": "2", "value": "ok-2", "nested": {"ts": ts}}}


def test_to_json_list_mixed():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert json.loads(Payload.to_json([
        {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=ts))
        },
        {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=ts))
        }
    ])) == [{'data': {'id': '1',
                      'nested': {'ts': '1970-01-01T00:00:00Z'},
                      'value': 'ok-1'},
             'item': 1},
            {'data': {'id': '2',
                      'nested': {'ts': '1970-01-01T00:00:00Z'},
                      'value': 'ok-2'},
             'item': 2}]


def test_to_obj_list_mixed():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert Payload.to_obj([
        {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=ts))
        },
        {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=ts))
        }
    ]) == [{'data': {'id': '1',
                     'nested': {'ts': ts},
                     'value': 'ok-1'},
            'item': 1},
           {'data': {'id': '2',
                     'nested': {'ts': ts},
                     'value': 'ok-2'},
            'item': 2}]


def test_to_json_dict_mixed():
    assert json.loads(Payload.to_json({
        "item1": {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        },
        "item2": {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        }
    })) == {'item1': {'data': {'id': '1',
                               'nested': {'ts': '1970-01-01T00:00:00Z'},
                               'value': 'ok-1'},
                      'item': 1},
            'item2': {'data': {'id': '2',
                               'nested': {'ts': '1970-01-01T00:00:00Z'},
                               'value': 'ok-2'},
                      'item': 2}}


def test_to_obj_dict_mixed():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert Payload.to_obj({
        "item1": {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=ts))
        },
        "item2": {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=ts))
        }
    }) == {'item1': {'data': {'id': '1',
                              'nested': {'ts': ts},
                              'value': 'ok-1'},
                     'item': 1},
           'item2': {'data': {'id': '2',
                              'nested': {'ts': ts},
                              'value': 'ok-2'},
                     'item': 2}}


def test_to_json_dataobject():
    assert Payload.to_json(MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0, tz=timezone.utc)
        )
    )) == '{"id":"test","value":"ok","nested":{"ts":"1970-01-01T00:00:00Z"}}'


def test_to_obj_dataobject():
    ts = datetime.fromtimestamp(0, tz=timezone.utc)
    assert Payload.to_obj(MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=ts
        )
    )) == {"id": "test", "value": "ok", "nested": {"ts": ts}}


def test_from_json_python_types():
    assert Payload.from_json('{"value": "str"}', str) == "str"
    with pytest.raises(ValidationError):
        assert Payload.from_json('{"value": "str"}', int) == "str"
    assert Payload.from_json('{"value": 123}', int) == int(123)
    with pytest.raises(ValidationError):
        assert Payload.from_json('{"value": 123}', str) == "123"
    assert Payload.from_json('{"value": 123.45}', float) == float(123.45)
    assert Payload.from_json('{"value": true}', bool) is True
    assert Payload.from_json('{"custom": "str"}', str, key='custom') == "str"
    assert Payload.from_json('{"test": "dict"}', dict) == {'test': 'dict'}
    assert Payload.from_json('["test1", "test2"]', set) == {'test2', 'test1'}
    assert Payload.from_json('["test1", "test2"]', list) == ['test1', 'test2']


def test_from_obj_python_types():
    assert Payload.from_obj({"value": "str"}, str) == "str"
    assert Payload.from_obj({"value": 123}, int) == int(123)
    assert Payload.from_obj({"value": 123.45}, float) == float(123.45)
    assert Payload.from_obj({"value": True}, bool) is True
    assert Payload.from_obj({"custom": "str"}, str, key='custom') == "str"
    assert Payload.from_obj({"test": "dict"}, dict) == {'test': 'dict'}
    assert Payload.from_obj(["test1", "test2"], set) == {'test2', 'test1'}
    assert Payload.from_obj(["test1", "test2"], list) == ['test1', 'test2']


def test_from_json_dataobject():
    assert Payload.from_json(
        '{"id": "test", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData
    ) == MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        )
    )


def test_from_obj_dataobject():
    assert Payload.from_obj(
        {"id": "test", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}, MockData
    ) == MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        )
    )


def test_from_obj_dataobject_dict():
    ts = datetime.fromtimestamp(0.0).astimezone(timezone.utc)
    assert Payload.from_obj({
        "item1": {"id": "test1", "value": "ok", "nested": {"ts": ts}},
        "item2": {"id": "test2", "value": "ok", "nested": {"ts": ts}}
    }, Dict[str, MockData]) == {
        "item1": MockData(id='test1', value='ok', nested=MockNested(
            ts=ts
        )),
        "item2": MockData(id='test2', value='ok', nested=MockNested(
            ts=ts
        ))
    }


def test_from_obj_dataobject_list():
    ts = datetime.fromtimestamp(0.0).astimezone(timezone.utc)
    assert Payload.from_obj([
        {"id": "test1", "value": "ok", "nested": {"ts": ts}},
        {"id": "test2", "value": "ok", "nested": {"ts": ts}}
    ], List[MockData]) == [
        MockData(id='test1', value='ok', nested=MockNested(
            ts=ts
        )),
        MockData(id='test2', value='ok', nested=MockNested(
            ts=ts
        ))
    ]


def test_from_obj_list():
    assert Payload.from_obj([
        {"value": "ok1"},
        {"value": "ok2"}
    ], List[Dict[str, str]]) == [{"value": "ok1"}, {"value": "ok2"}]


def test_from_obj_dict():
    assert Payload.from_obj({
        "item1": {"value": "ok1"},
        "item2": {"value": "ok2"}
    }, Dict[str, Dict[str, str]]) == {
        "item1": {"value": "ok1"},
        "item2": {"value": "ok2"}
    }


def test_from_json_dataobject_validate_datatype():
    data = '{"id": "test", "value": "not-ok"}'
    with pytest.raises(ValueError):
        Payload.from_json(data, MockDataValidate)


def test_from_json_dataobject_validate_null():
    data = '{"id": "test", "value": null}'
    with pytest.raises(ValueError):
        Payload.from_json(data, MockDataValidate)


def test_from_json_dataobject_validate_missing():
    data = '{"id": "test"}'
    with pytest.raises(ValueError):
        Payload.from_json(data, MockDataValidate)


def test_from_obj_dataobject_validate():
    data = '{"id": "test", "value": "not-ok"}'
    with pytest.raises(ValueError):
        Payload.from_obj(data, MockDataValidate)


def test_from_json_dataobject_do_not_validate_null():
    data = '{"id": "test", "value": null}'
    assert Payload.from_json(data, MockDataNullable) \
        == MockDataNullable(id='test', value=None)  # type: ignore


@pytest.mark.skip(reason="Enable when pydantic.BaseModel is supported")
def test_from_json_dataobject_do_not_validate_missing():
    data = '{"id": "test"}'
    assert Payload.from_json(data, MockDataNullable) \
        == MockDataNullable(id='test', value=None)  # type: ignore


def test_from_obj_dataobject_do_not_validate_none():
    data = {"id": "test", "value": None}
    assert Payload.from_obj(data, MockDataNullable) \
        == MockDataNullable(id='test', value=None)  # type: ignore


@pytest.mark.skip(reason="Enable when pydantic.BaseModel is supported")
def test_from_obj_dataobject_do_not_validate_missing():
    data = {"id": "test"}
    assert Payload.from_obj(data, MockDataNullable) \
        == MockDataNullable(id='test', value=None)  # type: ignore


def test_to_json_dataobject_validate():
    with pytest.raises(ValidationError):
        MockDataValidate(id='test', value='not-ok')  # type: ignore


def test_to_obj_dataobject_validate():
    with pytest.raises(ValidationError):
        MockDataValidate(id='test', value='not-ok')  # type: ignore


def test_to_json_dataobject_nullable():
    data = MockDataNullable(id='test', value=None)  # type: ignore
    assert Payload.to_json(data) == '{"id":"test","value":null}'


def test_to_obj_dataobject_nullable_invalid_type():
    with pytest.raises(ValidationError):
        MockDataNullable(id='test', value='not-ok')  # type: ignore


def test_from_json_invalid_types():
    with pytest.raises(ValidationError):
        Payload.from_json('{"id": "1", "value": "ok-1", "nested": {"ts": "INVALID DATE"}}', MockData)

    with pytest.raises(ValidationError):
        Payload.from_json('{"id": 42, "value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData)


def test_from_obj_invalid_types():
    with pytest.raises(ValidationError):
        Payload.from_obj({"id": "1", "value": "ok-1", "nested": {"ts": "INVALID DATE"}}, MockData)

    with pytest.raises(ValidationError):
        Payload.from_obj({"id": 42, "value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}, MockData)


def test_from_json_missing_fields():
    with pytest.raises(ValidationError):
        Payload.from_json('{"id": "1", "value": "ok-1", "nested": {}', MockData)

    with pytest.raises(ValidationError):
        Payload.from_json('{"value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData)


def test_from_obj_missing_fields():
    with pytest.raises(ValidationError):
        Payload.from_obj({"id": "1", "value": "ok-1", "nested": {}}, MockData)

    with pytest.raises(ValidationError):
        Payload.from_obj({"value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}, MockData)


def test_from_json_malformed():
    with pytest.raises(ValidationError):
        Payload.from_json(
            '{"item1": {"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}', MockData)

    with pytest.raises(ValidationError):
        Payload.from_json('BAD STRING', MockData)


def test_to_json_invalid_types():
    with pytest.raises(ValidationError):
        Payload.to_json(
            MockData(id=42, value='ok-value', nested=MockNested(ts=datetime.now(tz=timezone.utc))))  # type: ignore

    with pytest.raises(ValidationError):
        Payload.to_json(MockData(id='1', value='ok-value', nested=MockNested(ts="NOT A DATETIME")))  # type: ignore


def test_to_obj_invalid_types():
    with pytest.raises(ValidationError):
        Payload.to_obj(
            MockData(id=42, value='ok-value', nested=MockNested(ts=datetime.now(tz=timezone.utc))))  # type: ignore

    with pytest.raises(ValidationError):
        Payload.to_obj(MockData(id='1', value='ok-value', nested=MockNested(ts="NOT A DATETIME")))  # type: ignore
