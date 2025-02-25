"""Support for plugin configuration"""

from typing import Optional

from hopeit.dataobjects import dataclass, dataobject, field


@dataobject
@dataclass
class DatasetSerialization:
    protocol: str
    location: str
    partition_dateformat: Optional[str] = None
    storage_settings: dict[str, str | int] = field(default_factory=dict)
