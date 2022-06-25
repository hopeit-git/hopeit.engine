"""
Storage/persistence asynchronous get/set key-values.
Backed by Redis
"""
from typing import Optional, Type, Generic, Any

import aioredis

from hopeit.dataobjects import DataObject
from hopeit.dataobjects.payload import Payload

__all__ = ['RedisStorage']


class RedisStorage(Generic[DataObject]):
    """
       Stores and retrieves dataobjects from Redis
       This class must be initialized with the method connect
       Example:
           ```
           redis_store = RedisStorage().connect(address="redis://hostname:6379")
           ```
    """
    def __init__(self):
        """
        Setups Redis connection
        """
        self._conn: Optional[aioredis.Redis] = None

    def connect(self, *, address: str) -> Any:
        """
        Creates a Redis connection pool

        :param address: str, address = "redis://hostname:6379/0?encoding=utf-8"
        """
        self._conn = aioredis.from_url(address)
        return self

    async def get(self, key: str, *, datatype: Type[DataObject]) -> Optional[DataObject]:
        """
        Retrieves value under specified key, converted to datatype

        :param key: str
        :param datatype: dataclass implementing @dataobject (@see DataObject)
        :return: instance of datatype or None if not found
        """
        assert self._conn
        payload_str = await self._conn.get(key)
        if payload_str:
            return Payload.from_json(payload_str, datatype)
        return None

    async def store(self, key: str, value: DataObject, **kwargs):
        """
        Stores value under specified key

        :param key: str
        :param value: DataObject, instance of dataclass annotated with @dataobject
        :param **kwargs: extra args

        """
        assert self._conn
        payload_str = str(Payload.to_json(value))
        await self._conn.set(key, payload_str, **kwargs)

    async def delete(self, key: str):
        """
        Delete specified key

        :param key: str, key to be deleted
        """
        assert self._conn
        await self._conn.delete(key)

    async def list(self, pattern: str = "*")-> List[str]:
        """
        Returns a list of keys matching `pattern`

        :param pattern: str
        """
        assert self._conn
        return await self._conn.keys(pattern)

