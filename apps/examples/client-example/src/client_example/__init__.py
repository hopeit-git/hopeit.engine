from hopeit.dataobjects import dataobject, dataclass


@dataobject
@dataclass
class CountAndSaveResult:
    count: int
    save_path: str
