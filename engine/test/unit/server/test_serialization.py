import base64

import sys

from hopeit.app.config import Serialization, Compression
from hopeit.dataobjects import dataobject
from hopeit.dataobjects.payload import Payload
from hopeit.server.serialization import serialize, deserialize


@dataobject
class Data:
    x: str
    y: int


data = Data(x="data", y=42)

ser = {
    Serialization.JSON_UTF8: b'{"x": "data", "y": 42}',
    Serialization.JSON_BASE64: b'eyJ4IjogImRhdGEiLCAieSI6IDQyfQ==',
}


def test_serialize():
    print(sys.version_info, sys.version)
    assert serialize(data, Serialization.JSON_UTF8, Compression.NONE) == \
        ser[Serialization.JSON_UTF8] == Payload.to_json(data).encode()
    assert serialize(data, Serialization.JSON_BASE64, Compression.NONE) == \
        ser[Serialization.JSON_BASE64] == base64.b64encode(Payload.to_json(data).encode())


def test_deserialize():
    assert deserialize(ser[Serialization.JSON_UTF8], Serialization.JSON_UTF8, Compression.NONE, Data) == data
    assert deserialize(ser[Serialization.JSON_BASE64], Serialization.JSON_BASE64, Compression.NONE, Data) == data


def test_serialize_primitives():
    assert serialize("test", Serialization.JSON_UTF8, Compression.NONE) == b'{"value": "test"}'
    assert deserialize(b'{"value": "test"}', Serialization.JSON_UTF8, Compression.NONE, str) == "test"

    assert serialize("test", Serialization.JSON_BASE64, Compression.NONE) == b'eyJ2YWx1ZSI6ICJ0ZXN0In0='
    assert deserialize(b'eyJ2YWx1ZSI6ICJ0ZXN0In0=', Serialization.JSON_BASE64, Compression.NONE, str) == "test"

    assert serialize(42, Serialization.JSON_UTF8, Compression.NONE) == b'{"value": 42}'
    assert deserialize(b'{"value": 42}', Serialization.JSON_UTF8, Compression.NONE, int) == 42

    assert serialize(42.5, Serialization.JSON_UTF8, Compression.NONE) == b'{"value": 42.5}'
    assert deserialize(b'{"value": 42.5}', Serialization.JSON_UTF8, Compression.NONE, float) == 42.5

    assert serialize(True, Serialization.JSON_UTF8, Compression.NONE) == b'{"value": true}'
    assert deserialize(b'{"value": true}', Serialization.JSON_UTF8, Compression.NONE, bool) is True


def test_serialize_collections():
    assert serialize({"test": "value"}, Serialization.JSON_UTF8, Compression.NONE) == b'{"test": "value"}'
    assert deserialize(b'{"test": "value"}', Serialization.JSON_UTF8, Compression.NONE, dict) == {"test": "value"}

    assert serialize(["test", "value"], Serialization.JSON_UTF8, Compression.NONE) == b'["test", "value"]'
    assert deserialize(b'["test", "value"]', Serialization.JSON_UTF8, Compression.NONE, list) == ["test", "value"]

    assert serialize({"test", "value"}, Serialization.JSON_UTF8, Compression.NONE) == b'["test", "value"]' \
        or serialize({"test", "value"}, Serialization.JSON_UTF8, Compression.NONE) == b'["value", "test"]'
    assert deserialize(b'["test", "value"]', Serialization.JSON_UTF8, Compression.NONE, set) == {"test", "value"}
