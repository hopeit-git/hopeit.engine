"""
Client example module schemas
"""
from hopeit.dataobjects import dataobject


@dataobject
class CountAndSaveResult:
    count: int
    save_path: str
