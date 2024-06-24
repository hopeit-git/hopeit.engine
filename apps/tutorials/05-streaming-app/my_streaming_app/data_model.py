"""
Data Model for my_app
"""
from enum import Enum

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class MyData:
    text: str


class Status(str, Enum):
    NEW = 'NEW'
    VALID = 'VALID'
    PROCESSED = 'PROCESSED'


@dataobject
@dataclass
class MyMessage:
    text: str
    status: Status
