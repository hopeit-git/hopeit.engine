from dataclasses import dataclass, field
from typing import List

from hopeit.dataobjects import dataobject


@dataobject
@dataclass
class LogBatch:
    data: List[str]


@dataobject
@dataclass
class LogEventData:
    data: list


@dataobject
@dataclass
class RequestStats:
    request_id: str
    total: int
    done: int
    failed: int
