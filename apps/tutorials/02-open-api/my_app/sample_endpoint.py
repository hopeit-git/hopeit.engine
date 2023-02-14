"""
API: sample-endpoint
--------------
Same as first app sample-endpoint now with Open API.

This endpoint adds the capability of json-schema validation and API docs.
[CommonMark syntax](http://spec.commonmark.org/)  MAY be used for rich text
representation.
"""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.dataobjects import dataobject

__steps__ = ['step1']


@dataobject
class MyObject:
    text: str
    length: int


__api__ = event_api(
    query_args=[('payload', str, "provide a 'string' to create 'MyObject'"),
                ('number', int, "number to be added to the 'length' of the payload of MyObject")],
    responses={
        200: (MyObject, "MyObject where name is the received string uppercased and number its length")
    }
)


async def step1(payload: str, context: EventContext, number: str) -> MyObject:
    text = payload.upper()
    length = len(payload) + int(number)
    return MyObject(text, length)
