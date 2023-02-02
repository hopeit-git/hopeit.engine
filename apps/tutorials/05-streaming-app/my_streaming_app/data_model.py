"""
Data Model for my_app
"""
from enum import Enum

from hopeit.dataobjects import dataobject


@dataobject
class MyData:
    text: str


class Status(str, Enum):
    NEW = 'NEW'
    VALID = 'VALID'
    PROCESSED = 'PROCESSED'


@dataobject
class MyMessage:
    text: str
    status: Status
