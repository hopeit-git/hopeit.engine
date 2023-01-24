from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook
from . import MockData

__steps__ = ['produce_messages']

logger, extra = app_extra_logger()


async def produce_messages(payload: str, context: EventContext) -> Spawn[MockData]:
    logger.info(context, "producing message")
    for i in range(3):
        yield MockData(value=f"stream: {payload}.{i}")


async def __postprocess__(payload: MockData, context: EventContext, response: PostprocessHook) -> MockData:
    return payload
