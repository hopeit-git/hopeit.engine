"""
Client example module schemas
"""
from hopeit.dataobjects import dataobject, dataclass


@dataobject
@dataclass
class CountAndSaveResult:
    count: int
    save_path: str
