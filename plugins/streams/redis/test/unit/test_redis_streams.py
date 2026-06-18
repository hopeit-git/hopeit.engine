import asyncio

import redis.asyncio as redis
from redis import ResponseError

from datetime import datetime, timezone

from hopeit.app.config import Compression, Serialization
from hopeit.dataobjects import dataclass, dataobject
from hopeit.server.config import AuthType, StreamsConfig

from hopeit.streams import StreamEvent
from hopeit.redis_streams import BlockingConnectionPool, RedisStreamManager

from . import MockEventHandler, TestStreamData
from copy import deepcopy


@dataobject(event_id="value", event_ts="ts")
@dataclass
class MockData:
    value: str
    ts: datetime


@dataclass
class MockInvalidDataEvent:
    value: str


async def create_stream_manager():
    settings = StreamsConfig()
    return await RedisStreamManager(address=MockRedisPool.test_url).connect(settings)


def patch_redis_client(monkeypatch):
    monkeypatch.setattr(BlockingConnectionPool, "from_url", MockRedisPool.from_url)
    monkeypatch.setattr(redis, "Redis", MockRedisPool.redis)


async def write_stream():
    mgr = await create_stream_manager()
    payload = MockData("test_value", datetime.fromtimestamp(0, tz=timezone.utc))
    res = await mgr.write_stream(
        stream_name="test_stream",
        queue=TestStreamData.test_queue,
        payload=payload,
        track_ids=MockEventHandler.test_track_ids,
        auth_info={"auth_type": AuthType.UNSECURED, "allowed": "true"},
        target_max_len=10,
        compression=Compression.NONE,
        serialization=Serialization.JSON_UTF8,
    )
    assert res == 1
    assert mgr._write_pool.xadd_name == "test_stream"
    assert mgr._write_pool.xadd_maxlen == 10
    written_fields = mgr._write_pool.xadd_fields
    assert written_fields == {
        "id": "test_value",
        "type": "unit.test_redis_streams.MockData",
        "submit_ts": written_fields["submit_ts"],
        "event_ts": "1970-01-01T00:00:00+00:00",
        "track.operation_id": "test_operation_id",
        "track.request_id": "test_request_id",
        "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
        "track.session_id": "test_session_id",
        "comp": "none",
        "ser": "json",
        "auth_info": b"eyJhdXRoX3R5cGUiOiAiVW5zZWN1cmVkIiwgImFsbG93ZWQiOiAidHJ1ZSJ9",
        "payload": '{"value":"test_value","ts":"1970-01-01T00:00:00Z"}'.encode(),
        "queue": TestStreamData.test_queue.encode(),
    }
    res = await mgr.write_stream(
        stream_name="test_stream_no_maxlen",
        queue=TestStreamData.test_queue,
        payload=payload,
        track_ids=MockEventHandler.test_track_ids,
        auth_info={"auth_type": AuthType.UNSECURED, "allowed": "true"},
        compression=Compression.NONE,
        serialization=Serialization.JSON_UTF8,
    )
    assert res == 1
    assert mgr._write_pool.xadd_name == "test_stream_no_maxlen"
    assert mgr._write_pool.xadd_maxlen is None
    await mgr.close()


async def ensure_consumer_group():
    mgr = await create_stream_manager()
    await mgr.ensure_consumer_group(stream_name="test_stream", consumer_group="test_group")
    assert mgr._read_pool.xgroup_name == "test_stream"
    assert mgr._read_pool.xgroup_groupname == "test_group"
    assert mgr._read_pool.xgroup_latest_id == "0"
    assert mgr._read_pool.xgroup_mkstream is True
    await mgr.ensure_consumer_group(stream_name="test_stream", consumer_group="test_group")
    assert mgr._read_pool.xgroup_exists
    await mgr.close()


async def read_stream():
    mgr = await create_stream_manager()
    await mgr.ensure_consumer_group(stream_name="test_stream", consumer_group="test_group")
    count = 0
    for stream_event in await mgr.read_stream(
        stream_name="test_stream",
        consumer_group="test_group",
        datatypes={"unit.test_redis_streams.MockData": MockData},
        track_headers=MockEventHandler.test_track_ids.keys(),
        offset=">",
        batch_size=10,
        batch_interval=1000,
        timeout=1,
    ):
        assert stream_event.msg_internal_id == b"0000000000-0"
        assert stream_event.queue == TestStreamData.test_queue
        assert stream_event.payload == MockData("test_value", stream_event.payload.ts)
        for k, v in TestStreamData.test_track_ids.items():
            assert k in stream_event.track_ids
            if k != "stream.read_ts":
                assert v == stream_event.track_ids[k]
        count += 1
    assert count == MockRedisPool.message_count


async def read_stream_empty_batch():
    mgr = await create_stream_manager()
    count = 0
    for _ in await mgr.read_stream(
        stream_name="test_stream",
        consumer_group="empty_batch",
        datatypes={"MockData": MockData},
        track_headers=TestStreamData.test_track_ids.keys(),
        offset=">",
        batch_size=1,
        batch_interval=1000,
        timeout=1,
    ):
        assert False
    assert count == 0


async def ack_read_stream():
    stream_event = StreamEvent(
        msg_internal_id=b"0000000000-0",
        queue=TestStreamData.test_queue,
        payload=TestStreamData.test_payload,
        track_ids=TestStreamData.test_track_ids,
        auth_info={"auth_type": AuthType.UNSECURED, "allowed": "true"},
    )
    msg_id = b"0000000000-0"
    mgr = await create_stream_manager()
    await mgr.ensure_consumer_group(stream_name="test_stream", consumer_group="test_group")
    res = await mgr.ack_read_stream(
        stream_name="test_stream", consumer_group="test_group", stream_event=stream_event
    )
    assert res == 1
    assert mgr._read_pool.xack_msg_id == msg_id


async def test_write_stream(monkeypatch):
    patch_redis_client(monkeypatch)
    await write_stream()


async def test_ensure_consume_group(monkeypatch):
    patch_redis_client(monkeypatch)
    await ensure_consumer_group()


async def test_read_stream(monkeypatch):
    patch_redis_client(monkeypatch)
    await read_stream()


async def test_read_stream_queue_name(monkeypatch):
    patch_redis_client(monkeypatch)
    monkeypatch.setattr(TestStreamData, "test_queue", "custom")
    test_msg = deepcopy(MockRedisPool.test_msg)
    test_msg[1][b"queue"] = b"custom"
    monkeypatch.setattr(MockRedisPool, "test_msg", test_msg)
    await read_stream()


async def test_read_stream_default_queue_name_when_missing(monkeypatch):
    patch_redis_client(monkeypatch)
    test_msg = deepcopy(MockRedisPool.test_msg)
    del test_msg[1][b"queue"]
    monkeypatch.setattr(MockRedisPool, "test_msg", test_msg)
    await read_stream()


async def test_read_stream_empty_batch(monkeypatch):
    patch_redis_client(monkeypatch)
    await read_stream_empty_batch()


async def test_ack_read_stream(monkeypatch):
    patch_redis_client(monkeypatch)
    await ack_read_stream()


async def test_connect_uses_blocking_pool_settings(monkeypatch):
    patch_redis_client(monkeypatch)
    settings = StreamsConfig(max_connections=3, pool_timeout=2.5, protocol=2)
    mgr = await RedisStreamManager(address=MockRedisPool.test_url).connect(settings)
    assert mgr._write_pool.connection_kwargs == {
        "username": "",
        "password": "",
        "max_connections": 3,
        "timeout": 2.5,
        "protocol": 2,
    }
    assert mgr._read_pool.connection_kwargs == mgr._write_pool.connection_kwargs
    assert mgr._write_pool is not mgr._read_pool
    await mgr.close()
    assert mgr._write_pool is None
    assert mgr._read_pool is None


async def test_write_stream_concurrent_low_max_connections(monkeypatch):
    patch_redis_client(monkeypatch)
    settings = StreamsConfig(max_connections=2, pool_timeout=2.5)
    mgr = await RedisStreamManager(address=MockRedisPool.test_url).connect(settings)
    payload = MockData("test_value", datetime.fromtimestamp(0, tz=timezone.utc))
    results = await asyncio.gather(
        *(
            mgr.write_stream(
                stream_name="test_stream",
                queue=TestStreamData.test_queue,
                payload=payload,
                track_ids=MockEventHandler.test_track_ids,
                auth_info={"auth_type": AuthType.UNSECURED, "allowed": "true"},
                compression=Compression.NONE,
                serialization=Serialization.JSON_UTF8,
            )
            for _ in range(10)
        )
    )
    assert results == [1] * 10
    assert mgr._write_pool.max_active_connections <= 2
    await mgr.close()


class MockRedisPool:
    test_url: str = "redis://test_url"
    message_count = 10
    test_msg = [
        b"0000000000-0",
        {
            b"type": b"unit.test_redis_streams.MockData",
            b"track.request_id": b"test_request_id",
            b"track.request_ts": b"2020-02-05T17:07:37.771396+00:00",
            b"track.session_id": b"test_session_id",
            b"submit_ts": b"2020-02-05T17:07:38.771396+00:00",
            b"event_ts": b"",
            b"id": b"test_id",
            b"comp": b"none",
            b"ser": b"json",
            b"auth_info": b"eyJhdXRoX3R5cGUiOiAiVW5zZWN1cmVkIiwgImFsbG93ZWQiOiAidHJ1ZSJ9",
            b"payload": b'{"value": "test_value", "ts": "1970-01-01T00:00:00+00:00"}',
            b"queue": b"AUTO",
        },
    ]

    def __init__(self, *, connection_kwargs=None):
        self.connection_kwargs = connection_kwargs or {}
        max_connections = self.connection_kwargs.get("max_connections")
        self._semaphore = asyncio.Semaphore(max_connections) if max_connections else None
        self._active_connections = 0
        self.max_active_connections = 0
        self.xadd_name = None
        self.xadd_fields = None
        self.xadd_maxlen = None
        self.xgroup_name = None
        self.xgroup_groupname = None
        self.xgroup_latest_id = None
        self.xgroup_mkstream = None
        self.xgroup_exists = False
        self.xread_consumername = None
        self.xack_msg_id = None
        self.closed = False
        self.aclosed = False

    @staticmethod
    def from_url(url, **kwargs):
        assert url == MockRedisPool.test_url
        return MockRedisPool(connection_kwargs=kwargs)

    @staticmethod
    def redis(*, connection_pool):
        return connection_pool

    async def xadd(self, name, fields, id=b"*", maxlen=None, approximate=True):
        if self._semaphore:
            async with self._semaphore:
                return await self._xadd(name, fields, id, maxlen, approximate)
        return await self._xadd(name, fields, id, maxlen, approximate)

    async def _xadd(self, name, fields, id=b"*", maxlen=None, approximate=True):
        self._active_connections += 1
        self.max_active_connections = max(self.max_active_connections, self._active_connections)
        await asyncio.sleep(0)
        try:
            self.xadd_name = name
            self.xadd_fields = fields
            self.xadd_maxlen = maxlen
            self.xadd_approximate = approximate
            return 1
        finally:
            self._active_connections -= 1

    async def xgroup_create(self, name, groupname, id="$", mkstream=False):
        if self.xgroup_name == name and self.xgroup_groupname == groupname:
            self.xgroup_exists = True
            raise ResponseError
        self.xgroup_name = name
        self.xgroup_groupname = groupname
        self.xgroup_latest_id = id
        self.xgroup_mkstream = mkstream

    async def xreadgroup(self, groupname, consumername, streams, count=None, block=None):
        if groupname == "empty_batch":
            return []
        assert self.xgroup_groupname == groupname
        assert {self.xgroup_name: ">"} == streams
        self.xread_consumername = consumername
        return [[self.xgroup_name, [MockRedisPool.test_msg for _ in range(count)]]]

    async def xack(self, name, groupname, id, *ids):
        assert self.xgroup_groupname == groupname
        assert self.xgroup_name == name
        self.xack_msg_id = id
        return 1

    async def close(self):
        self.closed = True

    async def aclose(self, close_connection_pool=None):
        assert close_connection_pool is True
        self.aclosed = True
