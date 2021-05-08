"""
Streams module. Handles reading and writing to streams.
Backed by Redis Streams
"""
from abc import ABC
import os
import socket
from datetime import datetime, timezone
from typing import Dict, List, Any, Union
from dataclasses import dataclass
from importlib import import_module

from hopeit.app.config import Compression, Serialization
from hopeit.dataobjects import EventPayload
from hopeit.server.config import AuthType, StreamsConfig
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


class StreamConfigError(Exception):
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
    @staticmethod
    def create(config: StreamsConfig):
        sm_comps = config.stream_manager.split('.')
        module_name, impl_name = '.'.join(sm_comps[:-1]), sm_comps[-1]
        logger.info(__name__, f"Importing StreamManager module: {module_name} implementation: {impl_name}...")
        module = import_module(module_name)
        impl = getattr(module, impl_name)
        logger.info(__name__, f"Creating {impl_name} with connection_str: {config.connection_str}...")
        return impl(address=config.connection_str)

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


class NoStreamManager(StreamManager):
    """
    Default noop implementation for StreamManager that will fail if no Stream Manager is specified in
    server config file. Applications using streams will fail to start a server if
    `stream_manager` is not properly specified in configuration file.
    """
    def __init__(self, *, address: str):
        raise StreamConfigError(
            "Cannot start engine StreamManager, "
            "a valid `stream_manager` implementation needs to be specified."
            "\n You need to install a proper Stream Manager."
            "\n i.e. to use Redis Streams: "
            "\n 1) Install `hopeit.engine` with redis-streams plugin: `pip install hopeit.engine[redis-streams]`"
            "\n 2) Add the following entry to server config json file under `streams` section:"
            '"stream_manager": "hopeit.redis_streams.RedisStreamManager", '
            "\nCheck Plugins/ -> Streams docs section for available additional options."
        )
