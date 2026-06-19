from functools import partial

from hopeit.dataobjects import dataclass, dataobject, field
from pydantic import SecretStr


@dataobject
@dataclass
class RedisAuthSettings:
    username: SecretStr = field(default_factory=partial(SecretStr, ""))
    password: SecretStr = field(default_factory=partial(SecretStr, ""))


@dataobject
@dataclass
class RedisPoolSettings:
    max_connections: int = 100
    pool_timeout: float = 10.0
    protocol: int = 2
