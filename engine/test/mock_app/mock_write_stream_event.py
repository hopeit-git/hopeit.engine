from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from . import MockData

__steps__ = ['produce_message']

logger, extra = app_extra_logger()


async def produce_message(payload: str, context: EventContext) -> MockData:
    logger.info(context, "producing message")
    return MockData(f"stream: {payload}")
