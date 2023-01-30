import asyncio

from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext

__steps__ = ['wait']

from mock_app import MockData, MockResult

logger, extra = app_extra_logger()


async def wait(payload: MockData, context: EventContext) -> MockResult:
    logger.info(context, "mock_stream_timeout.wait")
    if payload.value == "timeout":
        logger.info(context, "simulating timeout...")
        await asyncio.sleep(30.0)
        logger.info(context, "done simulating timeout.")
    return MockResult(value="ok: ok")
