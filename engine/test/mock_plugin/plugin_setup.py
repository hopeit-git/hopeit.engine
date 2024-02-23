"""
test setup event plugin mode
"""

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger


__steps__ = ["setup"]

initialized = False

logger, extra = app_extra_logger()


async def setup(payload: None, context: EventContext):
    global initialized
    initialized = True
    logger.info(context, "Setup done")
