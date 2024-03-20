"""
Provides generic `serialize`, `deserialize` methods to handle payloads
"""

import base64
import pickle
from typing import Type

from hopeit.app.config import Serialization, Compression

__all__ = ["serialize", "deserialize"]

from hopeit.dataobjects import EventPayload, EventPayloadType
from hopeit.dataobjects.payload import Payload
from hopeit.server.compression import compress, decompress


async def _ser_json_utf8(data: EventPayload, level: int) -> bytes:
    return Payload.to_json(data).encode("utf-8")


async def _deser_json_utf8(
    data: bytes, datatype: Type[EventPayloadType]
) -> EventPayload:
    return Payload.from_json(data.decode("utf-8"), datatype)


async def _ser_pickle(data: EventPayload, level: int) -> bytes:
    return pickle.dumps(data, protocol=level)


async def _deser_pickle(data: bytes, datatype: Type[EventPayloadType]) -> EventPayload:
    return pickle.loads(data)


async def _ser_json_base64(data: EventPayload, level: int) -> bytes:
    return base64.b64encode(await _ser_json_utf8(data, level))


async def _deser_json_base64(
    data: bytes, datatype: Type[EventPayloadType]
) -> EventPayload:
    return await _deser_json_utf8(base64.b64decode(data), datatype)


_SERDESER = {
    Serialization.JSON_UTF8: (_ser_json_utf8, 0, _deser_json_utf8),
    Serialization.JSON_BASE64: (_ser_json_base64, 0, _deser_json_base64),
    Serialization.PICKLE3: (_ser_pickle, 3, _deser_pickle),
    Serialization.PICKLE4: (_ser_pickle, 4, _deser_pickle),
    Serialization.PICKLE5: (_ser_pickle, 5, _deser_pickle),
}


async def serialize(
    data: EventPayload, serialization: Serialization, compression: Compression
) -> bytes:
    algos = _SERDESER[serialization]
    encoded = await algos[0](data, level=algos[1])
    return compress(encoded, compression)


async def deserialize(
    data: bytes,
    serialization: Serialization,
    compression: Compression,
    datatype: Type[EventPayloadType],
) -> EventPayload:
    algos = _SERDESER[serialization]
    decomp = decompress(data, compression)
    return await algos[2](decomp, datatype)
