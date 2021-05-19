"""
Streams module. Handles reading and writing to streams.
Backed by Redis Streams
"""
import asyncio
import json
import base64
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Union, Tuple, Optional, NamedTuple

from hopeit.app.config import Compression, Serialization
from hopeit.dataobjects import EventPayload
from hopeit.server.serialization import deserialize, serialize
from hopeit.server.logger import engine_logger, extra_logger
from hopeit.streams import StreamManager, StreamEvent, StreamOSError

from hopeit.samsa.client import SamsaClient
from hopeit.samsa import Batch, Message

logger = engine_logger()
extra = extra_logger()


class SamsaStreamManager(StreamManager):
    """
    Manages streams of a Hopeit App using Samsa hopeit plugin
    """
    class ConnectionStr(NamedTuple):
        api_version: str
        push_nodes: str
        consume_nodes: str
    
    def __init__(self, *, address: str):
        """
        Creates an StreamManager instance backed by redis connection
        specified in `address`.

        After creation, `connect()` must be called to create connection pools.
        """
        self.address = address
        self.api_version, push_nodes_str, consume_nodes_str = \
            self._parse_connection_str(address)
        self.push_nodes = push_nodes_str.split(',')
        self.consume_nodes = consume_nodes_str.split(',')
        self.consumer_id = self._consumer_id()
        self._client: Optional[SamsaClient] = None

    def _parse_connection_str(self, address: str) -> ConnectionStr:
        values = dict([
            tuple(x.split('=')) for x in address.split(';') if x
        ])
        print("************** address", values)
        return self.ConnectionStr(**values)

    async def connect(self):
        """
        Connects to Redis using two connection pools, one to handle
        writing to stream and one for reading.
        """
        logger.info(__name__, f"Connecting address={self.address}...")
        try:
            self._client = SamsaClient(
                push_nodes=self.push_nodes, 
                consume_nodes=self.consume_nodes,
                api_version=self.api_version,
                consumer_id=self.consumer_id
            )
            return self
        except (OSError, IOError) as e:
            logger.error(__name__, e)
            raise StreamOSError(e) from e

    async def close(self):
        """
        Close connections if active
        """

    def _get_client(self) -> SamsaClient:
        if self._client is None:
            raise StreamOSError("Samsa client not initialized.")
        return self._client

    async def write_stream(self, *,
                           stream_name: str,
                           queue: str,
                           payload: EventPayload,
                           track_ids: Dict[str, str],
                           auth_info: Dict[str, Any],
                           compression: Compression,
                           serialization: Serialization,
                           target_max_len: int = 0) -> int:
        """
        Writes event (push) to a Samsa stream using SamsaClient

        :param stream_name: stream name or key used by Redis
        :param queue tag to be added to the message (it does not affect stream_name at this point)
        :param payload: EventPayload, a special type of dataclass object decorated with `@dataobject`
        :param track_ids: dict with key and id values to track in stream event
        :param auth_info: dict with auth info to be tracked as part of stream event
        :param compression: Compression, supported compression algorithm from enum
        :param target_max_len: int, max_len to indicate approx. target collection size to Redis,
            default 0 will not send max_len to Redis.
        :return: number of successful written messages
        """
        message = self._encode_message(
            payload, track_ids, auth_info, compression, serialization, queue
        )
        batch = Batch(items=[message])
        res = await self._get_client().push(
            batch, stream_name=stream_name, maxlen=target_max_len
        )
        return len(res)

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
            batch = await self._get_client().consume(
                stream_name=stream_name,
                consumer_group=consumer_group,
                batch_size=batch_size,
                timeout_ms=timeout
            )

            if batch.missed > 0:
                logger.warning(__name__, "Consumer missed messages from stream", extra=extra(
                    stream_name=stream_name,
                    consumer_group=consumer_group,
                    missed=batch.missed
                ))

            msg_count = len(batch.items)
            if msg_count != 0:
                logger.debug(__name__, "Received batch", extra=extra(
                    prefix='stream.', name=stream_name, consumer_group=consumer_group,
                    batch_size=msg_count, head=batch.items[0].key, tail=batch.items[-1].key)
                )
                stream_events: List[Union[StreamEvent, Exception]] = []
                for msg in batch.items:
                    read_ts = datetime.now().astimezone(tz=timezone.utc).isoformat()
                    datatype = datatypes.get(msg.datatype)
                    if datatype is None:
                        err_msg = \
                            f"Cannot read msg_id={msg.key}: msg_type={msg.datatype} is not any of {datatypes}"
                        stream_events.append(TypeError(err_msg))
                    else:
                        stream_events.append(
                            self._decode_message(
                                msg, datatype, stream_name, consumer_group, track_headers, read_ts
                            )
                        )
                return stream_events

            #  Wait some time if no messages to prevent race condition in connection pool
            await asyncio.sleep(batch_interval / 1000.0)
            return []
        except (OSError, IOError) as e:
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
        return 1

    def _encode_message(self, payload: EventPayload,
                        track_ids: Dict[str, str],
                        auth_info: Dict[str, Any],
                        compression: Compression,
                        serialization: Serialization,
                        queue: str) -> Message:
        return Message(
            key=payload.event_id(),  # type: ignore
            datatype=type(payload).__name__,
            submit_ts=datetime.now().astimezone(tz=timezone.utc).isoformat(),
            event_ts=self._event_ts(payload),
            track_ids=track_ids,
            auth_info=base64.b64encode(json.dumps(auth_info).encode()).decode(),
            ser=serialization,
            comp=compression,
            queue=queue
        ).encode(
            payload=serialize(payload, serialization, compression)
        )

    def _event_ts(self, payload: EventPayload) -> Optional[str]:
        event_ts = payload.event_ts()  # type: ignore
        if isinstance(event_ts, datetime):
            return event_ts.astimezone(tz=timezone.utc).isoformat()
        if isinstance(event_ts, str):
            return event_ts
        return None

    def _decode_message(self, msg: Message, datatype: type, 
                        stream_name: str, consumer_group: str,
                        track_headers: List[str], read_ts: str):
        return StreamEvent(
            msg_internal_id=msg.key.encode(),
            queue=msg.queue,
            payload=deserialize(
                msg.payload, msg.ser, msg.comp, datatype),  # type: ignore
            track_ids={
                'stream.name': stream_name,
                'stream.queue': msg.queue,
                'stream.msg_id': msg.key,
                'stream.consumer_group': consumer_group,
                'stream.submit_ts': msg.submit_ts,
                'stream.event_ts': msg.event_ts or '',
                'stream.event_id': msg.key,
                'stream.read_ts': read_ts,
                **{
                    k: (msg.track_ids.get(k) or '')
                    for k in track_headers
                },
                'track.operation_id': str(uuid.uuid4()),
            },
            auth_info=json.loads(base64.b64decode(msg.auth_info.encode()))
        )
