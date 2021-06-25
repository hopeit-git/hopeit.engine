import pytest
import json
from datetime import datetime, timezone

from hopeit.dataobjects.jsonify import Json

from . import MockNested, MockData, MockDataValidate, MockDataDoNotValidate


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


def test_to_obj_python_types():
    assert Json.to_obj('str', key='test') == {"test": "str"}
    assert Json.to_obj(123, key='test') == {"test": 123}
    assert Json.to_obj(123.45, key='test') == {"test": 123.45}
    assert Json.to_obj(True, key='test') == {"test": True}
    assert Json.to_obj({'test': 'dict'}) == {"test": "dict"}
    assert Json.to_obj({'test2', 'test1'}) == ["test1", "test2"]
    assert Json.to_obj(['test2', 'test1']) == ["test2", "test1"]


def test_to_json_list_dataobject():
    assert json.loads(Json.to_json([
        MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    ])) == [{"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
            {"id": "2", "value": "ok-2", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}]


def test_to_obj_list_dataobject():
    assert Json.to_obj([
        MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    ]) == [{"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
           {"id": "2", "value": "ok-2", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}]


def test_to_json_dict_dataobject():
    assert json.loads(Json.to_json({
        'item1': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        'item2': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    })) == {"item1": {"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
            "item2": {"id": "2", "value": "ok-2", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}}


def test_to_obj_dict_dataobject():
    assert Json.to_obj({
        'item1': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
        'item2': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc))),
    }) == {"item1": {"id": "1", "value": "ok-1", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
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


def test_to_obj_list_mixed():
    assert Json.to_obj([
        {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        },
        {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        }
    ]) == [{'data': {'id': '1',
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


def test_to_obj_dict_mixed():
    assert Json.to_obj({
        "item1": {
            'item': 1,
            'data': MockData(id='1', value='ok-1', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        },
        "item2": {
            'item': 2,
            'data': MockData(id='2', value='ok-2', nested=MockNested(ts=datetime.fromtimestamp(0, tz=timezone.utc)))
        }
    }) == {'item1': {'data': {'id': '1',
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


def test_to_obj_dataobject():
    assert Json.to_obj(MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0, tz=timezone.utc)
        )
    )) == {"id": "test", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}


def test_from_json_python_types():
    assert Json.from_json('{"value": "str"}', str) == "str"
    assert Json.from_json('{"value": 123}', int) == int(123)
    assert Json.from_json('{"value": 123.45}', float) == float(123.45)
    assert Json.from_json('{"value": true}', bool) is True
    assert Json.from_json('{"custom": "str"}', str, key='custom') == "str"
    assert Json.from_json('{"test": "dict"}', dict) == {'test': 'dict'}
    assert Json.from_json('["test1", "test2"]', set) == {'test2', 'test1'}
    assert Json.from_json('["test1", "test2"]', list) == ['test1', 'test2']


def test_from_obj_python_types():
    assert Json.from_obj({"value": "str"}, str) == "str"
    assert Json.from_obj({"value": 123}, int) == int(123)
    assert Json.from_obj({"value": 123.45}, float) == float(123.45)
    assert Json.from_obj({"value": True}, bool) is True
    assert Json.from_obj({"custom": "str"}, str, key='custom') == "str"
    assert Json.from_obj({"test": "dict"}, dict) == {'test': 'dict'}
    assert Json.from_obj(["test1", "test2"], set) == {'test2', 'test1'}
    assert Json.from_obj(["test1", "test2"], list) == ['test1', 'test2']


def test_from_json_dataobject():
    assert Json.from_json(
        '{"id": "test", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData
    ) == MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        )
    )


def test_from_obj_dataobject():
    assert Json.from_obj(
        {"id": "test", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}, MockData
    ) == MockData(
        id='test',
        value='ok',
        nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        )
    )


def test_from_obj_dataobject_dict():
    assert Json.from_obj({
        "item1": {"id": "test1", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
        "item2": {"id": "test2", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}
    }, dict, item_datatype=MockData) == {
        "item1": MockData(id='test1', value='ok', nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        )),
        "item2": MockData(id='test2', value='ok', nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        ))
    }


def test_from_obj_dataobject_list():
    assert Json.from_obj([
        {"id": "test1", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}},
        {"id": "test2", "value": "ok", "nested": {"ts": "1970-01-01T00:00:00+00:00"}}
    ], list, item_datatype=MockData) == [
        MockData(id='test1', value='ok', nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        )),
        MockData(id='test2', value='ok', nested=MockNested(
            ts=datetime.fromtimestamp(0.0).astimezone(timezone.utc)
        ))
    ]


def test_from_obj_list():
    assert Json.from_obj([
        {"value": "ok1"},
        {"value": "ok2"}
    ], list, key='value', item_datatype=str) == ["ok1", "ok2"]


def test_from_obj_dict():
    assert Json.from_obj({
        "item1": {"value": "ok1"},
        "item2": {"value": "ok2"}
    }, dict, key='value', item_datatype=str) == {
        "item1": "ok1",
        "item2": "ok2"
    }


def test_from_json_dataobject_validate():
    data = '{"id": "test", "value": "not-ok"}'
    with pytest.raises(ValueError):
        Json.from_json(data, MockDataValidate)


def test_from_obj_dataobject_validate():
    data = '{"id": "test", "value": "not-ok"}'
    with pytest.raises(ValueError):
        Json.from_obj(data, MockDataValidate)


def test_from_json_dataobject_do_not_validate():
    data = '{"id": "test", "value": "not-ok"}'
    assert Json.from_json(data, MockDataDoNotValidate) \
        == MockDataDoNotValidate(id='test', value='not-ok')  # type: ignore


def test_from_obj_dataobject_do_not_validate():
    data = {"id": "test", "value": "not-ok"}
    assert Json.from_obj(data, MockDataDoNotValidate) \
        == MockDataDoNotValidate(id='test', value='not-ok')  # type: ignore


def test_to_json_dataobject_validate():
    data = MockDataValidate(id='test', value='not-ok')  # type: ignore
    with pytest.raises(ValueError):
        Json.to_json(data)


def test_to_obj_dataobject_validate():
    data = MockDataValidate(id='test', value='not-ok')  # type: ignore
    with pytest.raises(ValueError):
        Json.to_obj(data)


def test_to_json_dataobject_do_not_validate():
    data = MockDataDoNotValidate(id='test', value='not-ok')  # type: ignore
    assert Json.to_json(data) == '{"id": "test", "value": "not-ok"}'


def test_to_obj_dataobject_do_not_validate():
    data = MockDataDoNotValidate(id='test', value='not-ok')  # type: ignore
    assert Json.to_obj(data) == {"id": "test", "value": "not-ok"}


def test_from_json_invalid_types():
    with pytest.raises(ValueError):
        Json.from_json('{"id": "1", "value": "ok-1", "nested": {"ts": "INVALID DATE"}}', MockData)

    with pytest.raises(ValueError):
        Json.from_json('{"id": 42, "value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData)


def test_from_obj_invalid_types():
    with pytest.raises(ValueError):
        Json.from_obj({"id": "1", "value": "ok-1", "nested": {"ts": "INVALID DATE"}}, MockData)

    with pytest.raises(ValueError):
        Json.from_obj({"id": 42, "value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}, MockData)


def test_from_json_missing_fields():
    with pytest.raises(ValueError):
        Json.from_json('{"id": "1", "value": "ok-1", "nested": {}', MockData)

    with pytest.raises(ValueError):
        Json.from_json('{"value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}', MockData)


def test_from_obj_missing_fields():
    with pytest.raises(ValueError):
        Json.from_obj({"id": "1", "value": "ok-1", "nested": {}}, MockData)

    with pytest.raises(ValueError):
        Json.from_obj({"value": 42, "nested": {"ts": "1970-01-01T00:00:00+00:00"}}, MockData)


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


def test_to_obj_invalid_types():
    with pytest.raises(ValueError):
        Json.to_obj(
            MockData(id=42, value='ok-value', nested=MockNested(ts=datetime.now(tz=timezone.utc))))  # type: ignore

    with pytest.raises(ValueError):
        Json.to_obj(MockData(id='1', value='ok-value', nested=MockNested(ts="NOT A DATETIME")))  # type: ignore
