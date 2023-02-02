from typing import Optional

from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from . import MockData, MockResult

__steps__ = ['produce_messages', SHUFFLE, 'consume_stream', 'generate_default']

logger, extra = app_extra_logger()


async def produce_messages(payload: str, context: EventContext) -> Spawn[MockData]:
    logger.info(context, "producing message")
    for i in range(3):
        yield MockData(value=f"stream.{payload}.{i}")


async def consume_stream(payload: MockData, context: EventContext) -> Optional[MockResult]:
    logger.info(context, "consuming message", extra=extra(value=payload.value))
    _, data, occ = payload.value.split('.')
    if data == 'fail':
        raise AssertionError("Test for error")
    if data == 'none':
        return None
    return MockResult(value="ok: " + data + '.' + occ)


async def generate_default(payload: None, context: EventContext) -> MockResult:
    logger.info(context, "creating default result")
    return MockResult(value="default")
