"""Support for plugin configuration"""

from functools import partial
from typing import Optional

from hopeit.dataobjects import dataclass, dataobject, field

from pydantic import SecretStr


@dataobject
@dataclass
class DatasetSerialization:
    protocol: str
    location: str
    partition_dateformat: Optional[str] = None
    storage_settings: dict[str, str | int] = field(default_factory=dict)


@dataobject
@dataclass
class DataframesDatabaseSettings:
    database_key: str
    dataset_serialization: DatasetSerialization


@dataobject
@dataclass
class DataframesRegistryConfig:
    save_location: str
    connection_str: str = "<<NotSpecified>>"
    username: SecretStr = field(default_factory=partial(SecretStr, ""))
    password: SecretStr = field(default_factory=partial(SecretStr, ""))


@dataobject
@dataclass
class DataframesSettings:
    registry: DataframesRegistryConfig
    default_database: DataframesDatabaseSettings
