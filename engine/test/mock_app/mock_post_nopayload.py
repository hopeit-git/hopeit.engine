from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

__steps__ = ["entry_point"]

logger, extra = app_extra_logger()


def entry_point(payload: None, context: EventContext, query_arg1: str) -> str:
    logger.info(context, "mock_post_nopayload.entry_point")
    return f"ok: nopayload {query_arg1}"
