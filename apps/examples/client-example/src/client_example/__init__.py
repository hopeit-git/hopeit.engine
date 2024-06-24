"""
Client example module schemas
"""
from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class CountAndSaveResult:
    count: int
    save_path: str
