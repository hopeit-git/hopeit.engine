"""
Data model for simple-benchmark benchmark application
"""
from datetime import datetime
from typing import List, Optional
from enum import Enum
from dataclasses import dataclass, field

from hopeit.dataobjects import dataobject
from hopeit.dataobjects.validation import validate
from hopeit.toolkit.validators import pattern, non_empty_str


class StatusType(Enum):
    NEW = 'NEW'
    LOADED = 'LOADED'
    SUBMITTED = 'SUBMITTED'
    PROCESSED = 'PROCESSED'


@dataobject
@dataclass
class Status:
    """Status change"""
    ts: datetime
    type: StatusType


@dataobject
@dataclass
@validate(
    id=non_empty_str(),
    name=pattern('.+')
)
class User:
    """User information"""
    id: str
    name: str


@dataobject(event_id='id', event_ts='status.ts')
@dataclass
@validate(
    id=non_empty_str()
)
class Something:
    """Example Something event"""
    id: str
    user: User
    status: Optional[Status] = None
    history: List[Status] = field(default_factory=list)


@dataobject
@dataclass
class SomethingParams:
    """Params to create and save Something"""
    id: str
    user: str


@dataobject
@dataclass
class SomethingNotFound:
    """Item not found in datastore"""
    path: str
    id: str
