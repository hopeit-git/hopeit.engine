"""
Storage/persistence asynchronous get/set key-values.
Backed by Redis
"""
from typing import Optional, Type, Generic, Any

import aioredis  # type: ignore

from hopeit.dataobjects import DataObject
from hopeit.dataobjects.payload import Payload

__all__ = ['RedisStorage']


class RedisStorage(Generic[DataObject]):
    """
       Stores and retrieves dataobjects from Redis
       This class must be initialized with the method connect
       Example:
           ```
           redis_store = await RedisStorage().connect(address="redis://hostname:6379")
           ```
    """
    def __init__(self):
        """
        Setups Redis connection
        """
        self._conn: Optional[aioredis.Redis] = None

    async def connect(self, *, address: str) -> Any:
        """
        Creates a Redis connection pool

        :param address: str, address = "redis://hostname:6379/0?encoding=utf-8"
        """
        self._conn = await aioredis.create_redis_pool(address)
        return self

    async def get(self, key: str, *, datatype: Type[DataObject]) -> Optional[DataObject]:
        """
        Retrieves value under specified key, converted to datatype

        :param key: str
        :param datatype: dataclass implementing @dataobject (@see DataObject)
        :return: instance of datatype or None if not found
        """
        assert self._conn
        payload_str = await self._conn.get(key, encoding='utf-8')
        if payload_str:
            return Payload.from_json(payload_str, datatype)
        return None

    async def store(self, key: str, value: DataObject):
        """
        Stores value under specified key

        :param key: str
        :param value: DataObject, instance of dataclass annotated with @dataobject
        """
        assert self._conn
        payload_str = str(Payload.to_json(value))
        await self._conn.set(key, payload_str)
