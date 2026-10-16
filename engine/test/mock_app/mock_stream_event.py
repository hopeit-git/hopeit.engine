from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from . import MockData, MockResult

__steps__ = ["consume_stream"]

logger, extra = app_extra_logger()


async def consume_stream(payload: MockData, context: EventContext) -> MockResult | None:
    logger.info(context, "consuming message", extra=extra(value=payload.value))
    if payload.value == "fail":
        raise AssertionError("Test for error")
    return MockResult("ok: " + payload.value)
