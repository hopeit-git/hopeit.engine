from datetime import datetime

from hopeit.dataobjects import dataobject


@dataobject
class MockNested:
    ts: datetime


@dataobject(event_id='id', event_ts='nested.ts')
class MockData:
    id: str
    value: str
    nested: MockNested


@dataobject(event_id='id')
class MockDataWithoutTs:
    id: str
    value: str


@dataobject
class MockDataWithAutoEventId:
    value: str


# TODO: support @dataobject(frozen=True)
@dataobject
class MockDataValidate:
    id: str
    value: int


@dataobject(validate=False)
class MockDataDoNotValidate:
    id: str
    value: int
