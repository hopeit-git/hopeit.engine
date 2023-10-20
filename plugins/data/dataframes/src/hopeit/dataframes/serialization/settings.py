from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class DatasetSerialization:
    protocol: str
    location: str
