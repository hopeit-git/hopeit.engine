from uuid import uuid4
from dataclasses import dataclass
from fnmatch import fnmatch
import pytest  # type: ignore
import redis.asyncio as redis
from hopeit.dataobjects import dataobject
from hopeit.dataobjects.payload import Payload

from hopeit.redis_storage import RedisStorage


@dataobject
@dataclass
class RedisMockData:
    test: str


test_key = str(uuid4())
test_url = "redis://localhost"
payload_str = """{"test": "test_redis"}"""
test_redis = RedisMockData(test='test_redis')


async def store_item():
    redis = RedisStorage().connect(address=test_url)
    await redis.store(test_key, test_redis)
    assert test_key in redis._conn.items
    assert redis._conn.items[test_key] == Payload.to_json(test_redis)


async def store_item_extra_args():
    redis = RedisStorage().connect(address=test_url)
    await redis.store(test_key, test_redis, ex=60)  # ttl 60 secconds
    assert redis._conn.set_called_with == {'ex': 60}
    assert test_key in redis._conn.items
    assert redis._conn.items[test_key] == Payload.to_json(test_redis)


async def get_item():
    redis = RedisStorage().connect(address=test_url)
    get_str = await redis.get(test_key, datatype=RedisMockData)
    assert get_str == test_redis
    assert type(get_str) is RedisMockData


async def get_item_not_found():
    redis = RedisStorage().connect(address=test_url)
    get_str = await redis.get(test_key + "_other", datatype=RedisMockData)
    assert get_str is None


async def delete_item():
    redis = RedisStorage().connect(address=test_url)
    assert redis._conn.items.get(test_key) is not None
    await redis.delete(test_key)
    assert redis._conn.items.get(test_key) is None


async def delete_items():
    redis = RedisStorage().connect(address=test_url)
    await redis.store('my_key1', test_redis)
    await redis.store('my_key2', test_redis)
    await redis.delete('my_key1', 'my_key2')
    assert redis._conn.items.get('my_key1') is None
    assert redis._conn.items.get('my_key2') is None


async def list_objects():
    redis = RedisStorage().connect(address=test_url)
    files = await redis.list_objects()
    assert files == [test_key]
    files = await redis.list_objects(wildcard="my_key*")
    assert files == []
    await redis.store('my_key1', test_redis)
    await redis.store('my_key2', test_redis)
    files = await redis.list_objects(wildcard="my_key*")
    assert files == ['my_key1', 'my_key2']


async def connect():
    redis = RedisStorage().connect(address=test_url)
    assert type(redis._conn) is MockRedisPool
    assert type(redis) is RedisStorage


class MockRedisPool:
    def __init__(self):
        self.items: dict = {test_key: payload_str}
        self.set_called_with = None

    async def get(self, key: str):
        return self.items.get(key, None)

    async def set(self, key: str, payload: str, **kwargs):
        self.set_called_with = kwargs
        self.items[key] = payload

    async def delete(self, *keys: str):
        for key in keys:
            del self.items[key]

    async def keys(self, pattern: str):
        if pattern == "*":
            return [k.encode('utf-8') for k in self.items]
        return [k.encode('utf-8') for k in self.items if fnmatch(k, pattern)]

    @staticmethod
    def from_url(url):
        assert url == test_url
        return MockRedisPool()


@pytest.mark.asyncio
async def test_set(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await store_item()


async def test_set_extra_args(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await store_item_extra_args()


@pytest.mark.asyncio
async def test_get(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await get_item()


@pytest.mark.asyncio
async def test_delete(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await delete_item()
    await delete_items()


@pytest.mark.asyncio
async def test_list_objects(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await list_objects()


@pytest.mark.asyncio
async def test_get_item_not_found(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await get_item_not_found()


@pytest.mark.asyncio
async def test_connect(monkeypatch):
    monkeypatch.setattr(redis, 'from_url', MockRedisPool.from_url)
    await connect()
