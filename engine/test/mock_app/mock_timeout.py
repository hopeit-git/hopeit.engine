import asyncio

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

__steps__ = ["wait"]

logger, extra = app_extra_logger()


async def wait(payload: None, context: EventContext, *, delay: int) -> str:
    logger.info(context, "mock_timeout.delay", extra=extra(delay=delay))
    await asyncio.sleep(float(delay))
    return "ok"
