"""
Common validation module that can be shared among events in simple-example test app
"""
from typing import Optional

from hopeit.app.context import EventContext
from model import Something


def validate(payload: Optional[Something], *, context: EventContext) -> Optional[Something]:
    return payload
