"""
Streams module. Handles reading and writing to streams.
Backed by Redis Streams
"""
from abc import ABC
import os
import socket
import json
import base64
from datetime import datetime, timezone
from typing import Dict, List, Any, Union
from dataclasses import dataclass

from hopeit.app.config import Compression, Serialization
from hopeit.dataobjects import EventPayload
from hopeit.server.serialization import serialize
from hopeit.server.config import AuthType
from hopeit.server.logger import engine_logger, extra_logger

logger = engine_logger()
extra = extra_logger()

__all__ = ['StreamEvent',
           'StreamManager',
           'stream_auth_info',
           'StreamOSError']


@dataclass
class StreamEvent:
    msg_internal_id: bytes
    payload: EventPayload
    track_ids: Dict[str, str]
    auth_info: Dict[str, Any]


class StreamOSError(Exception):
    pass


def stream_auth_info(stream_event: StreamEvent):
    return {
        **stream_event.auth_info,
        'auth_type': AuthType(stream_event.auth_info.get('auth_type', 'Unsecured')),
    }


class StreamManager(ABC):
    """
    Base class to imeplement stream management of a Hopeit App
    """
    async def connect(self):
        """
        Connects to Redis using two connection pools, one to handle
        writing to stream and one for reading.
        """
        raise NotImplementedError()

    async def close(self):
        """
        Close connections to Redis
        """
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        raise NotImplementedError()

    @staticmethod
    def as_data_event(payload: EventPayload) -> EventPayload:
        """
        Checks payload for implementing `@dataobject` decorator.
        Raises NotImplementedError if payload does not implement `@dataobject`

        :param payload: dataclass object decorated with `@dataobject`
        :return: same payload as received
        """
        if not getattr(payload, '__data_object__', False):
            raise NotImplementedError(
                f"{type(payload)} must be decorated with `@dataobject` to be used in streams")
        return payload

    def _fields(self, payload: EventPayload,
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

    def _consumer_id(self) -> str:
        """
        Constructs a consumer id for this instance

        :return: str, concatenating current UTC ISO datetime, host name, process id
            and this StreamManager instance id
        """
        ts = datetime.now().astimezone(tz=timezone.utc).isoformat()
        host = socket.gethostname()
        pid = os.getpid()
        mgr = id(self)
        return f"{ts}.{host}.{pid}.{mgr}"
