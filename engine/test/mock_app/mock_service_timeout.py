import asyncio

from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from . import MockData

__steps__ = ['message']

logger, extra = app_extra_logger()


async def __service__(context: EventContext) -> Spawn[MockData]:
    i = 0
    while True:
        i += 1
        logger.info(context, f"service: producing message {i}")
        yield MockData("timeout")


async def message(payload: MockData, context: EventContext) -> MockData:
    logger.info(context, f"service: timing-out on message {payload}")
    await asyncio.sleep(5.0)  # timeout!
    return payload
