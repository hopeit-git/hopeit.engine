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
    :field protocol: int: Redis protocol version to use. Default is 2.
    """

    max_connections: int = 100
    pool_timeout: float = 10.0
    protocol: int = 2
