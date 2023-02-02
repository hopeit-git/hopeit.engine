from hopeit.app.context import EventContext
from hopeit.dataobjects import dataobject

__steps__ = ['step1']


@dataobject
class MyObject:
    text: str
    length: int


async def step1(payload: str, context: EventContext) -> MyObject:
    """
    Receives a string and returns MyObject where name is the received string
    uppercased and number its length
    """
    text = payload.upper()
    length = len(payload)
    return MyObject(text, length)
