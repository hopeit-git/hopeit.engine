from dataclasses import dataclass
from enum import Enum
from typing import List
from hopeit.dataobjects import DataObject, dataobject


@dataobject
@dataclass
class StreamStorageItem:
    prefix: str
    key: str
    data: DataObject


@dataobject
@dataclass
class StreamStorageBatch:
    items: List[StreamStorageItem]


class Result(Enum):
    OK = "OK"

    
@dataobject
@dataclass
class StreamStorageOp:
    result: Result
    info: str
