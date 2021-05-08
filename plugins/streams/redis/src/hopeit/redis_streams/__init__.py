"""
Streams module. Handles reading and writing to streams.
Backed by Redis Streams
"""
import asyncio
import json
import base64
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Union

import aioredis  # type: ignore
from aioredis import RedisError

from hopeit.app.config import Compression, Serialization
from hopeit.dataobjects import EventPayload
from hopeit.server.serialization import deserialize, serialize
from hopeit.server.logger import engine_logger, extra_logger
from hopeit.streams import StreamManager, StreamEvent, StreamOSError

logger = engine_logger()
extra = extra_logger()


class RedisStreamManager(StreamManager):
    """
    Manages streams of a Hopeit App
    """

    def __init__(self, *, address: str):
        """
        Creates an StreamManager instance backed by redis connection
        specified in `address`.
        After creation, `connect()` must be called to create connection pools.
        """
        self.address = address
        self.consumer_id = self._consumer_id()
        self._write_pool: aioredis.Redis = None
        self._read_pool: aioredis.Redis = None

    async def connect(self):
        """
        Connects to Redis using two connection pools, one to handle
        writing to stream and one for reading.
        """
        logger.info(__name__, f"Connecting address={self.address}...")
        try:
            self._write_pool = await aioredis.create_redis_pool(self.address)
            self._read_pool = await aioredis.create_redis_pool(self.address)
            return self
        except (OSError, RedisError) as e:  # pragma: no cover
            logger.error(__name__, e)
            raise StreamOSError(e) from e

    async def close(self):
        """
        Close connections to Redis
        """

        async def _close(pool) -> None:
            if pool:
                pool.close()
                await pool.wait_closed()
            return None

        self._read_pool = await _close(self._read_pool)
        self._write_pool = await _close(self._write_pool)

    async def write_stream(self, *,
                           stream_name: str,
                           payload: EventPayload,
                           track_ids: Dict[str, str],
                           auth_info: Dict[str, Any],
                           compression: Compression,
                           serialization: Serialization,
                           target_max_len: int = 0) -> int:
        """
        Writes event to a Redis stream using XADD
        :param stream_name: stream name or key used by Redis
        :param payload: EventPayload, a special type of dataclass object decorated with `@dataobject`
        :param track_ids: dict with key and id values to track in stream event
        :param auth_info: dict with auth info to be tracked as part of stream event
        :param compression: Compression, supported compression algorithm from enum
        :param target_max_len: int, max_len to indicate approx. target collection size to Redis,
            default 0 will not send max_len to Redis.
        :return: number of successful written messages
        """
        event_fields = self._encode_message(payload, track_ids, auth_info, compression, serialization)
        ok = await self._write_pool.xadd(
            stream=stream_name, fields=event_fields,
            max_len=target_max_len if target_max_len > 0 else None,
            exact_len=False)
        return ok

    async def ensure_consumer_group(self, *,
                                    stream_name: str,
                                    consumer_group: str):
        """
        Ensures a consumer_group exists for a given stream.
        If group does not exists, XGROUP_CREATE will be executed in Redis and consumer group
        created to consume event from beginning of stream (from id=0)
        If group already exists a message will be logged and no action performed.
        If stream does not exists and empty stream will be created.
        :param stream_name: str, stream name or key used by Redis
        :param consumer_group: str, consumer group passed to Redis
        """
        try:
            await self._read_pool.xgroup_create(
                stream_name,
                consumer_group,
                latest_id='0',
                mkstream=True
            )
        except aioredis.errors.BusyGroupError:
            logger.info(__name__,
                        "Consumer_group already exists " +
                        f"read_stream={stream_name} consumer_group={consumer_group}")

    async def read_stream(self, *,
                          stream_name: str,
                          consumer_group: str,
                          datatypes: Dict[str, type],
                          track_headers: List[str],
                          offset: str,
                          batch_size: int,
                          timeout: int,
                          batch_interval: int) -> List[Union[StreamEvent, Exception]]:
        """
        Attempts reading streams using a consumer group,
        blocks for `timeout` seconds
        and yields asynchronously the deserialized objects gotten from the stream.
        In case timeout is reached, nothing is yielded
        and read_stream must be called again,
        usually in an infinite loop while app is running.
        :param stream_name: str, stream name or key used by Redis
        :param consumer_group: str, consumer group registered in Redis
        :param datatypes: Dict[str, type] supported datatypes name: type to be extracted from stream.
            Types need to support json deserialization using `@dataobject` annotation
        :param track_headers: list of headers/id fields to extract from message if available
        :param offset: str, last msg id consumed to resume from. Use'>' to consume unconsumed events,
            or '$' to consume upcoming events
        :param batch_size: max number of messages to process on each iteration
        :param timeout: time to block waiting for messages, in milliseconds
        :param batch_interval: int, time to sleep between requests to connection pool in case no
            messages are returned. In milliseconds. Used to prevent blocking the pool.
        :param compression: Compression, supported compression algorithm from enum
        :return: yields Tuples of message id (bytes) and deserialized DataObject
        """
        try:
            batch = await self._read_pool.xread_group(
                consumer_group,
                self.consumer_id,
                streams=[stream_name],
                latest_ids=[offset],
                count=batch_size,
                timeout=timeout
            )

            msg_count = len(batch)

            if msg_count != 0:
                logger.debug(__name__, "Received batch",
                             extra=extra(prefix='stream.', name=stream_name, consumer_group=consumer_group,
                                         batch_size=msg_count, head=batch[0][1], tail=batch[-1][1]))
                stream_events: List[Union[StreamEvent, Exception]] = []
                for msg in batch:
                    read_ts = datetime.now().astimezone(tz=timezone.utc).isoformat()
                    msg_type = msg[2][b'type'].decode()
                    datatype = datatypes.get(msg_type)
                    if datatype is None:
                        err_msg = \
                            f"Cannot read msg_id={msg[1].decode()}: msg_type={msg_type} is not any of {datatypes}"
                        stream_events.append(TypeError(err_msg))
                    else:
                        stream_events.append(
                            self._decode_message(msg, datatype, consumer_group, track_headers, read_ts))
                return stream_events

            #  Wait some time if no messages to prevent race condition in connection pool
            await asyncio.sleep(batch_interval / 1000.0)
            return []
        except (OSError, RedisError) as e:  # pragma: no cover
            raise StreamOSError(e) from e

    async def ack_read_stream(self, *,
                              stream_name: str,
                              consumer_group: str,
                              stream_event: StreamEvent):
        """
        Acknowledges a read message to Redis streams.
        Acknowledged messages are removed from a pending list by Redis.
        This method should be called for every message that is properly
        received and processed with no errors.
        With this mechanism, messages not acknowledged can be retried.
        :param stream_name: str, stream name or key used by Redis
        :param consumer_group: str, consumer group registered with Redis
        :param stream_event: StreamEvent, as provided by `read_stream(...)` method
        """
        ack = await self._read_pool.xack(stream_name, consumer_group, stream_event.msg_internal_id)
        assert ack == 1
        return ack

    def _encode_message(self, payload: EventPayload,
                        track_ids: Dict[str, str],
                        auth_info: Dict[str, Any],
                        compression: Compression,
                        serialization: Serialization) -> dict:
        """
        Extract dictionary of fields to be sent to Redis from a DataEvent
        :param payload, DataEvent
        :return: dict of str containing:
            :id: extracted from payload.event_id() method
            :type: datatype name
            :submit_ts: datetime at the moment of this call, in UTC ISO format
            :event_ts: extracted from payload.event_ts() if defined, if not empty string
            :payload: json serialized payload
        """
        event_fields = {
            'id': payload.event_id(),  # type: ignore
            'type': type(payload).__name__,
            'submit_ts': datetime.now().astimezone(tz=timezone.utc).isoformat(),
            'event_ts': '',
            **{k: v or '' for k, v in track_ids.items()},
            'auth_info': base64.b64encode(json.dumps(auth_info).encode()),
            'ser': serialization.value,
            'comp': compression.value,
            'payload': serialize(payload, serialization, compression)
        }
        event_ts = payload.event_ts()  # type: ignore
        if isinstance(event_ts, datetime):
            event_fields['event_ts'] = \
                event_ts.astimezone(tz=timezone.utc).isoformat()
        elif isinstance(event_ts, str):
            event_fields['event_ts'] = event_ts
        return event_fields

    def _decode_message(self, msg: List[Union[bytes, Dict[bytes, bytes]]],
                        datatype: type, consumer_group: str,
                        track_headers: List[str], read_ts: str):
        assert isinstance(msg[0], bytes) and isinstance(msg[1], bytes) and isinstance(msg[2], dict), \
            "Invalid message format. Expected `[bytes, bytes, Dict[bytes, bytes]]`"
        compression = Compression(msg[2][b'comp'].decode())
        serialization = Serialization(msg[2][b'ser'].decode())
        return StreamEvent(
            msg_internal_id=msg[1],
            payload=deserialize(
                msg[2][b'payload'], serialization, compression, datatype),  # type: ignore
            track_ids={
                'stream.name': msg[0].decode(),
                'stream.msg_id': msg[1].decode(),
                'stream.consumer_group': consumer_group,
                'stream.submit_ts': msg[2][b'submit_ts'].decode(),
                'stream.event_ts': msg[2][b'event_ts'].decode(),
                'stream.event_id': msg[2][b'id'].decode(),
                'stream.read_ts': read_ts,
                **{
                    k: (msg[2].get(k.encode()) or b'').decode()
                    for k in track_headers
                },
                'track.operation_id': str(uuid.uuid4()),
            },
            auth_info=json.loads(base64.b64decode(msg[2].get(b'auth_info', b'{}')))
        )
