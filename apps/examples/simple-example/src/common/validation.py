"""
Common validation module that can be shared among events in simple-example test app
"""
from typing import Optional
from model import Something

from hopeit.app.context import EventContext


def validate(payload: Optional[Something], *, context: EventContext) -> Optional[Something]:
    return payload
