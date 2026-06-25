from functools import partial

from hopeit.dataobjects import dataclass, dataobject, field
from pydantic import SecretStr


@dataobject
@dataclass
class RedisAuthSettings:
    """
    Redis authentication settings.

    :field username: SecretStr: Username for authentication. Default is an empty secret string.
    :field password: SecretStr: Password for authentication. Default is an empty secret string.
    """

    username: SecretStr = field(default_factory=partial(SecretStr, ""))
    password: SecretStr = field(default_factory=partial(SecretStr, ""))


@dataobject
@dataclass
class RedisPoolSettings:
    """
    Redis connection pool settings.

    :field max_connections: int: Maximum Redis connections per stream connection pool.
        Default is 100.
    :field pool_timeout: float: Maximum seconds to wait for an available Redis connection.
        Default is 10.0.
    :field socket_timeout: float: Maximum seconds to wait for Redis socket read/write operations.
        Default is 30.0.
    :field socket_connect_timeout: float: Maximum seconds to wait for Redis socket connection.
        Default is 5.0.
    :field health_check_interval: float: Maximum seconds between Redis connection health checks.
        Default is 0.0, which disables periodic health checks.
    :field protocol: int: Redis protocol version to use. Default is 2.
    """

    max_connections: int = 100
    pool_timeout: float = 10.0
    socket_timeout: float = 30.0
    socket_connect_timeout: float = 5.0
    health_check_interval: float = 0.0
    protocol: int = 2
