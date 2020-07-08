from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext

__steps__ = ['entry_point']

logger, extra = app_extra_logger()


def entry_point(payload: str, context: EventContext) -> str:
    logger.info(context, "mock_post_auth.entry_point")
    return f"ok: {payload}"
