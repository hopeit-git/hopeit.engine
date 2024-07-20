"""Support for plugin configuration"""

from typing import Optional

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class DatasetSerialization:
    protocol: str
    location: str
    partition_dateformat: Optional[str] = None
