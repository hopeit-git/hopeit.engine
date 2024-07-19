"""
Storage/persistence asynchronous get/set key-values.
Backed by Redis
"""

from typing import Optional, Type, Generic, Any, List

import redis.asyncio as redis

from hopeit.dataobjects import DataObject
from hopeit.dataobjects.payload import Payload

__all__ = ["RedisStorage"]


class RedisStorage(Generic[DataObject]):
    """
    Stores and retrieves dataobjects from Redis
    This class must be initialized with the method connect
    Example:
        ```
        redis_store = RedisStorage().connect(address="redis://hostname:6379")
        ```
    """

    def __init__(self) -> None:
        """
        Setups Redis connection
        """
        self._conn: Optional[redis.Redis] = None

    def connect(self, *, address: str, username: str = "", password: str = "") -> Any:
        """
        Creates a Redis connection pool

        :param address: str, address = "redis://hostname:6379/0?encoding=utf-8"
        :param username: str: Username for authentication (default is "").
        :param password: str: Password for authentication (default is "").

        """
        self._conn = redis.from_url(address, username=username, password=password)
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
        :param **kwargs: You can use arguments expected by the set method in the redis library i.e.:
            ex sets an expire flag on key name for ex seconds.
            px sets an expire flag on key name for px milliseconds.
            nx if set to True, set the value at key name to value only if it does not exist.
            xx if set to True, set the value at key name to value only if it already exists.
            keepttl if True, retain the time to live associated with the key. (Available since Redis 6.0).
            *These arguments may vary depending on the version of redis installed.

        i.e. store object:
        ```
        redis_store.store(key='my_key', value=my_dataobject)
        ```

        i.e. store object with kwargs option, adding `ex=60` redis set a ttl of 60 seconds for the object:
        ```
        redis_store.store(key='my_key', value=my_dataobject, ex=60)
        ```

        """
        assert self._conn
        payload_str = str(Payload.to_json(value))
        await self._conn.set(key, payload_str, **kwargs)

    async def delete(self, *keys: str):
        """
        Delete specified keys

        :param keys: str, keys to be deleted
        """
        assert self._conn
        await self._conn.delete(*keys)

    async def list_objects(self, wildcard: str = "*") -> List[str]:
        """
        Returns a list of keys matching `wildcard`

        :param wildcard: str, expected glob-style wildcards
        """
        assert self._conn
        return [obj.decode("utf-8") for obj in await self._conn.keys(wildcard)]
