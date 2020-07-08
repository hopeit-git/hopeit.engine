from typing import Optional

from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from . import MockData, MockResult

__steps__ = ['entry_point', 'handle_ok_case', 'handle_special_case']

logger, extra = app_extra_logger()
initialized = False


async def __init_event__(context: EventContext):
    global initialized
    logger.info(context, "INIT")
    initialized = True


async def entry_point(payload: MockData, context: EventContext, *, query_arg1: str) -> Optional[MockData]:
    logger.info(context, "mock_post_event.entry_point", extra=extra(query_arg1=query_arg1))
    assert initialized
    if query_arg1 == 'fail':
        raise AssertionError("Test for error")
    assert payload.value == query_arg1
    if payload.value == 'ok':
        return MockData(value=payload.value)
    return None


def handle_special_case(payload: None, context: EventContext) -> MockResult:
    return MockResult("None")


def handle_ok_case(payload: MockData, context: EventContext) -> MockResult:
    return MockResult("ok: " + payload.value)
