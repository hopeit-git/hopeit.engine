import aioredis  # type: ignore

import pytest
from datetime import datetime, timezone
from dataclasses import dataclass

from hopeit.app.config import Compression, Serialization
from hopeit.dataobjects import dataobject
from hopeit.server.config import AuthType

from hopeit.streams import StreamEvent
from hopeit.redis_streams import RedisStreamManager

from . import MockEventHandler, TestStreamData
from copy import deepcopy


@dataobject(event_id='value', event_ts='ts')
@dataclass
class MockData:
    value: str
    ts: datetime


@dataclass
class MockInvalidDataEvent:
    value: str


async def create_stream_manager():
    return await RedisStreamManager(address=MockRedisPool.test_url).connect()


async def write_stream():
    mgr = await create_stream_manager()
    payload = MockData('test_value', datetime.fromtimestamp(0, tz=timezone.utc))
    res = await mgr.write_stream(
        stream_name='test_stream',
        queue=TestStreamData.test_queue,
        payload=payload,
        track_ids=MockEventHandler.test_track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'},
        target_max_len=10,
        compression=Compression.NONE,
        serialization=Serialization.JSON_UTF8
    )
    assert res == 1
    assert mgr._write_pool.xadd_stream_name == 'test_stream'
    assert mgr._write_pool.xadd_max_len == 10
    written_fields = mgr._write_pool.xadd_fields
    assert written_fields == {
        'id': 'test_value',
        'type': 'MockData',
        'submit_ts': written_fields['submit_ts'],
        'event_ts': '1970-01-01T00:00:00+00:00',
        'track.operation_id': 'test_operation_id',
        'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00',
        'track.session_id': 'test_session_id',
        'comp': 'none',
        'ser': 'json',
        'auth_info': b'eyJhdXRoX3R5cGUiOiAiVW5zZWN1cmVkIiwgImFsbG93ZWQiOiAidHJ1ZSJ9',
        'payload': '{"value": "test_value", "ts": "1970-01-01T00:00:00+00:00"}'.encode(),
        'queue': TestStreamData.test_queue.encode()
    }
    res = await mgr.write_stream(
        stream_name='test_stream_no_max_len',
        queue=TestStreamData.test_queue,
        payload=payload,
        track_ids=MockEventHandler.test_track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'},
        compression=Compression.NONE,
        serialization=Serialization.JSON_UTF8
    )
    assert res == 1
    assert mgr._write_pool.xadd_stream_name == 'test_stream_no_max_len'
    assert mgr._write_pool.xadd_max_len is None
    await mgr.close()


async def ensure_consumer_group():
    mgr = await create_stream_manager()
    await mgr.ensure_consumer_group(stream_name='test_stream', consumer_group='test_group')
    assert mgr._read_pool.xgroup_stream == 'test_stream'
    assert mgr._read_pool.xgroup_group_name == 'test_group'
    assert mgr._read_pool.xgroup_latest_id == '0'
    assert mgr._read_pool.xgroup_mkstream is True
    await mgr.ensure_consumer_group(stream_name='test_stream', consumer_group='test_group')
    assert mgr._read_pool.xgroup_exists
    await mgr.close()


async def read_stream():
    mgr = await create_stream_manager()
    await mgr.ensure_consumer_group(stream_name='test_stream', consumer_group='test_group')
    count = 0
    for stream_event in (await mgr.read_stream(
            stream_name='test_stream',
            consumer_group='test_group',
            datatypes={'MockData': MockData},
            track_headers=MockEventHandler.test_track_ids.keys(),
            offset='>',
            batch_size=10,
            batch_interval=1000,
            timeout=1)):
        assert stream_event.msg_internal_id == b'0000000000-0'
        assert stream_event.queue == TestStreamData.test_queue
        assert stream_event.payload == MockData('test_value', stream_event.payload.ts)
        for k, v in TestStreamData.test_track_ids.items():
            assert k in stream_event.track_ids
            if k != 'stream.read_ts':
                assert v == stream_event.track_ids[k]
        count += 1
    assert count == MockRedisPool.message_count


async def read_stream_empty_batch():
    mgr = await create_stream_manager()
    count = 0
    for _ in (await mgr.read_stream(
            stream_name='test_stream',
            consumer_group='empty_batch',
            datatypes={'MockData': MockData},
            track_headers=TestStreamData.test_track_ids.keys(),
            offset='>',
            batch_size=1,
            batch_interval=1000,
            timeout=1)):
        assert False
    assert count == 0


async def ack_read_stream():
    stream_event = StreamEvent(
        msg_internal_id=b'0000000000-0',
        queue=TestStreamData.test_queue,
        payload=TestStreamData.test_payload,
        track_ids=TestStreamData.test_track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    msg_id = b'0000000000-0'
    mgr = await create_stream_manager()
    await mgr.ensure_consumer_group(stream_name='test_stream', consumer_group='test_group')
    res = await mgr.ack_read_stream(
        stream_name='test_stream',
        consumer_group='test_group',
        stream_event=stream_event)
    assert res == 1
    assert mgr._read_pool.xack_msg_id == msg_id


@pytest.mark.asyncio
async def test_write_stream(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await write_stream()


@pytest.mark.asyncio
async def test_ensure_consume_group(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await ensure_consumer_group()


@pytest.mark.asyncio
async def test_read_stream(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await read_stream()


@pytest.mark.asyncio
async def test_read_stream_queue_name(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    monkeypatch.setattr(TestStreamData, 'test_queue', 'custom')
    test_msg = deepcopy(MockRedisPool.test_msg)
    test_msg[2][b'queue'] = b'custom'
    monkeypatch.setattr(MockRedisPool, 'test_msg', test_msg)
    await read_stream()


@pytest.mark.asyncio
async def test_read_stream_default_queue_name_when_missing(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    test_msg = deepcopy(MockRedisPool.test_msg)
    del test_msg[2][b'queue']
    monkeypatch.setattr(MockRedisPool, 'test_msg', test_msg)
    await read_stream()


@pytest.mark.asyncio
async def test_read_stream_empty_batch(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await read_stream_empty_batch()


@pytest.mark.asyncio
async def test_ack_read_stream(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await ack_read_stream()


class MockRedisPool(aioredis.Redis):
    test_url: str = 'redis://test_url'
    message_count = 10
    test_msg = [b'test_stream', b'0000000000-0', {
        b'type': b'MockData',
        b'track.request_id': b'test_request_id',
        b'track.request_ts': b'2020-02-05T17:07:37.771396+00:00',
        b'track.session_id': b'test_session_id',
        b'submit_ts': b'2020-02-05T17:07:38.771396+00:00',
        b'event_ts': b'',
        b'id': b'test_id',
        b'comp': b'none',
        b'ser': b'json',
        b'auth_info': b'eyJhdXRoX3R5cGUiOiAiVW5zZWN1cmVkIiwgImFsbG93ZWQiOiAidHJ1ZSJ9',
        b'payload': b'{"value": "test_value", "ts": "1970-01-01T00:00:00+00:00"}',
        b'queue': b'DEFAULT'
    }]

    def __init__(self):
        self.xadd_stream_name = None
        self.xadd_fields = None
        self.xadd_max_len = None
        self.xgroup_stream = None
        self.xgroup_group_name = None
        self.xgroup_latest_id = None
        self.xgroup_mkstream = None
        self.xgroup_exists = False
        self.xread_consumer_name = None
        self.xack_msg_id = None
        self.closing = False

    @staticmethod
    async def create_redis_pool(url):
        assert url == MockRedisPool.test_url
        return MockRedisPool()

    async def xadd(self, stream, fields, message_id=b'*', max_len=None,
                   exact_len=False):
        self.xadd_stream_name = stream
        self.xadd_fields = fields
        self.xadd_max_len = max_len
        return 1

    async def xgroup_create(self, stream, group_name, latest_id='$', mkstream=False):
        if self.xgroup_stream == stream and self.xgroup_group_name == group_name:
            self.xgroup_exists = True
            raise aioredis.errors.BusyGroupError('xgroup_exists')
        self.xgroup_stream = stream
        self.xgroup_group_name = group_name
        self.xgroup_latest_id = latest_id
        self.xgroup_mkstream = mkstream

    async def xread_group(self, group_name, consumer_name, streams, timeout=0,
                          count=None, latest_ids=None, no_ack=False):
        if group_name == 'empty_batch':
            return []
        assert [self.xgroup_stream] == streams
        assert self.xgroup_group_name == group_name
        self.xread_consumer_name = consumer_name
        return [MockRedisPool.test_msg for _ in range(MockRedisPool.message_count)]

    async def xack(self, stream, group_name, id, *ids):
        assert self.xgroup_group_name == group_name
        assert self.xgroup_stream == stream
        self.xack_msg_id = id
        return 1

    def close(self):
        self.closing = True

    async def wait_closed(self):
        assert self.closing is True
        self.closing = False
