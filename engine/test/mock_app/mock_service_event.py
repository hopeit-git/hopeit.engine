from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from . import MockData

__steps__ = ['message']

logger, extra = app_extra_logger()


async def __service__(context: EventContext) -> Spawn[str]:
    i = 0
    while True:
        logger.info(context, f"service: producing message {i}")
        yield f"stream: service.{i}"
        i += 1


async def message(payload: str, context: EventContext) -> MockData:
    return MockData(value=payload)
