"""SETUP event that configures Redis Streams clients with blocking connection pools."""

from hopeit.app.context import EventContext
from hopeit.redis_streams import RedisStreamManager
from hopeit.redis_streams.settings import RedisAuthSettings, RedisPoolSettings

import redis.asyncio as redis
from redis.asyncio import BlockingConnectionPool


__steps__ = [
    "init_redis_streams",
]


async def init_redis_streams(payload: None, context: EventContext) -> None:
    auth_settings = context.settings(key="redis_auth", datatype=RedisAuthSettings)
    pool_settings = context.settings(key="redis_pool", datatype=RedisPoolSettings)

    def connection_factory(address: str):
        return redis.Redis(
            connection_pool=BlockingConnectionPool.from_url(
                address,
                username=auth_settings.username.get_secret_value(),
                password=auth_settings.password.get_secret_value(),
                max_connections=pool_settings.max_connections,
                timeout=pool_settings.pool_timeout,
                socket_timeout=pool_settings.socket_timeout,
                socket_connect_timeout=pool_settings.socket_connect_timeout,
                health_check_interval=pool_settings.health_check_interval,
                protocol=pool_settings.protocol,
            )
        )

    RedisStreamManager.setup_connection_factory(connection_factory)
