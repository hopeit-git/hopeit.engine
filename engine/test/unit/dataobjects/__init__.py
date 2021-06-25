from datetime import datetime

from hopeit.dataobjects import dataobject, dataclass


@dataobject
@dataclass
class MockNested:
    ts: datetime


@dataobject(event_id='id', event_ts='nested.ts')
@dataclass
class MockData:
    id: str
    value: str
    nested: MockNested


@dataobject(event_id='id')
@dataclass
class MockDataWithoutTs:
    id: str
    value: str


@dataobject
@dataclass
class MockDataWithAutoEventId:
    value: str


@dataobject
@dataclass(frozen=True)
class MockDataImmutable:
    id: str
    value: str
    nested: MockNested


@dataobject(unsafe=True)
@dataclass
class MockDataUnsafe:
    id: str
    value: str
    nested: MockNested


@dataobject
@dataclass
class MockDataValidate:
    id: str
    value: int


@dataobject(validate=False)
@dataclass
class MockDataDoNotValidate:
    id: str
    value: int
