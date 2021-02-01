"""
Test app api part 2
"""
from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext

__steps__ = ['entry_point']

from mock_app import MockData

logger, extra = app_extra_logger()

__api__ = event_api(
    description="Description Test app api part 2",
    payload=(MockData, "MockData payload"),
    query_args=[('arg1', str, "Argument 1")],
    responses={
        200: int
    }
)


def entry_point(payload: MockData, context: EventContext, arg1: str) -> int:
    logger.info(context, "mock_app_api_post.entry_point")
    return len(payload.value) + len(arg1)
