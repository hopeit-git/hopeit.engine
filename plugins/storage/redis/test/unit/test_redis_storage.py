import uuid
from dataclasses import dataclass
import aioredis  # type: ignore

from hopeit.dataobjects import dataobject
from hopeit.dataobjects.jsonify import Json
from hopeit.redis_storage import RedisStorage
import pytest  # type: ignore


@dataobject
@dataclass
class RedisMockData:
    test: str


test_key = str(uuid.uuid4())
test_url = "redis://localhost"
payload_str = """{"test": "test_redis"}"""
test_redis = RedisMockData(test='test_redis')


async def store_item():
    redis = await RedisStorage().connect(address=test_url)
    await redis.store(test_key, test_redis)
    assert redis._conn.last_key == test_key
    assert redis._conn.last_payload == Json.to_json(test_redis)


async def get_item():
    redis = await RedisStorage().connect(address=test_url)
    get_str = await redis.get(test_key, datatype=RedisMockData)
    assert get_str == test_redis
    assert type(get_str) is RedisMockData


async def get_item_not_found():
    redis = await RedisStorage().connect(address=test_url)
    get_str = await redis.get(test_key + "_other", datatype=RedisMockData)
    assert get_str is None


async def connect():
    redis = await RedisStorage().connect(address=test_url)
    assert type(redis._conn) is MockRedisPool
    assert type(redis) is RedisStorage


class MockRedisPool:
    def __init__(self):
        self.last_key = None
        self.last_payload = None

    async def get(self, key: str, encoding: str):
        assert encoding == 'utf-8'
        if key == test_key:
            return payload_str
        return None

    async def set(self, key: str, payload: str):
        self.last_key = key
        self.last_payload = payload
        assert key == test_key
        assert payload == payload_str
        pass

    @staticmethod
    async def create_redis_pool(url):
        assert url == test_url
        return MockRedisPool()


@pytest.mark.asyncio
async def test_set(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await store_item()


@pytest.mark.asyncio
async def test_get(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await get_item()


@pytest.mark.asyncio
async def test_get_item_not_found(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await get_item_not_found()


@pytest.mark.asyncio
async def test_connect(monkeypatch):
    monkeypatch.setattr(aioredis, 'create_redis_pool', MockRedisPool.create_redis_pool)
    await connect()
