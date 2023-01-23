from datetime import datetime
from typing import Optional

from pydantic import StrictStr
from hopeit.dataobjects import dataobject


@dataobject
class MockNested:
    ts: datetime


@dataobject(event_id='id', event_ts='nested.ts')
class MockData:
    id: str
    value: str
    nested: MockNested


@dataobject(event_id='id', event_ts='nested.ts')
class MockDataStrict:
    id: StrictStr
    value: str
    nested: MockNested


@dataobject(event_id='id')
class MockDataWithoutTs:
    id: str
    value: str


@dataobject
class MockDataWithAutoEventId:
    value: str


@dataobject
class MockDataFrozen:
    class Config:
        allow_mutation=False

    id: str
    value: int


@dataobject
class MockDataValidate:
    id: StrictStr
    value: int


@dataobject
class MockDataOptional:
    id: str
    value: Optional[int]
