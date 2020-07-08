import base64
import pickle
from dataclasses import dataclass
import sys

from hopeit.app.config import Serialization, Compression
from hopeit.dataobjects import dataobject
from hopeit.server.serialization import serialize, deserialize

pickle5_available = (sys.version_info.major > 3) or ((sys.version_info.major == 3) and (sys.version_info.minor >= 8))


@dataobject
@dataclass
class Data:
    x: str
    y: int


data = Data("data", 42)

ser = {
    Serialization.JSON_UTF8: b'{"x": "data", "y": 42}',
    Serialization.JSON_BASE64: b'eyJ4IjogImRhdGEiLCAieSI6IDQyfQ==',
    Serialization.PICKLE3: (
        b'\x80\x03ctest_serialization\nData\nq\x00)\x81q\x01}q\x02(X\x01\x00\x00\x00xq'
        b'\x03X\x04\x00\x00\x00dataq\x04X\x01\x00\x00\x00yq\x05K*ub.'),
    Serialization.PICKLE4: (
        b'\x80\x04\x958\x00\x00\x00\x00\x00\x00\x00\x8c\x12test_serialization\x94'
        b'\x8c\x04Data\x94\x93\x94)\x81\x94}\x94(\x8c\x01x\x94\x8c\x04data\x94\x8c\x01'
        b'y\x94K*ub.'),
    Serialization.PICKLE5: (
        b'\x80\x05\x958\x00\x00\x00\x00\x00\x00\x00\x8c\x12test_serialization\x94'
        b'\x8c\x04Data\x94\x93\x94)\x81\x94}\x94(\x8c\x01x\x94\x8c\x04data\x94\x8c\x01'
        b'y\x94K*ub.')
}


def test_serialize():
    print(sys.version_info, sys.version)
    assert serialize(data, Serialization.JSON_UTF8, Compression.NONE) == \
        ser[Serialization.JSON_UTF8] == data.to_json().encode()
    assert serialize(data, Serialization.JSON_BASE64, Compression.NONE) == \
        ser[Serialization.JSON_BASE64] == base64.b64encode(data.to_json().encode())
    assert serialize(data, Serialization.PICKLE3, Compression.NONE) == \
        ser[Serialization.PICKLE3] == pickle.dumps(data, 3)
    assert serialize(data, Serialization.PICKLE4, Compression.NONE) == \
        ser[Serialization.PICKLE4] == pickle.dumps(data, 4)
    if pickle5_available:
        assert serialize(data, Serialization.PICKLE5, Compression.NONE) == \
            ser[Serialization.PICKLE5] == pickle.dumps(data, 5)


def test_deserialize():
    assert deserialize(ser[Serialization.JSON_UTF8], Serialization.JSON_UTF8, Compression.NONE, Data) == data
    assert deserialize(ser[Serialization.JSON_BASE64], Serialization.JSON_BASE64, Compression.NONE, Data) == data
    assert deserialize(ser[Serialization.PICKLE3], Serialization.PICKLE3, Compression.NONE, Data) == data
    assert deserialize(ser[Serialization.PICKLE4], Serialization.PICKLE4, Compression.NONE, Data) == data
    if pickle5_available:
        assert deserialize(ser[Serialization.PICKLE5], Serialization.PICKLE5, Compression.NONE, Data) == data


def test_serialize_primitives():
    assert serialize("test", Serialization.JSON_UTF8, Compression.NONE) == b'{"value": "test"}'
    assert deserialize(b'{"value": "test"}', Serialization.JSON_UTF8, Compression.NONE, str) == "test"

    assert serialize("test", Serialization.JSON_BASE64, Compression.NONE) == b'eyJ2YWx1ZSI6ICJ0ZXN0In0='
    assert deserialize(b'eyJ2YWx1ZSI6ICJ0ZXN0In0=', Serialization.JSON_BASE64, Compression.NONE, str) == "test"

    assert serialize("test", Serialization.PICKLE3, Compression.NONE) == b'\x80\x03X\x04\x00\x00\x00testq\x00.'
    assert deserialize(b'\x80\x03X\x04\x00\x00\x00testq\x00.', Serialization.PICKLE3, Compression.NONE, str) == "test"

    assert serialize("test", Serialization.PICKLE4, Compression.NONE) == \
        b'\x80\x04\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04test\x94.'
    assert deserialize(b'\x80\x04\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04test\x94.',
                       Serialization.PICKLE4, Compression.NONE, str) == "test"
    if pickle5_available:
        assert serialize("test", Serialization.PICKLE5, Compression.NONE) == \
            b'\x80\x05\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04test\x94.'
        assert deserialize(b'\x80\x05\x95\x08\x00\x00\x00\x00\x00\x00\x00\x8c\x04test\x94.',
                           Serialization.PICKLE5, Compression.NONE, str) == "test"

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
