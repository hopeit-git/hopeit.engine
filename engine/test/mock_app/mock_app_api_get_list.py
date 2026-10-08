"""
NO TITLE HERE, Title in __api__

Description of Test app api list
"""

from typing import List, Optional

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from mock_app import MockData

logger, extra = app_extra_logger()

__steps__ = ["entry_point"]

__api__ = event_api(
    summary="Test app api list",
    query_args=[("arg1", Optional[int], "Argument 1")],
    responses={200: (List[MockData], "MockData result")},
)


def entry_point(
    payload: None, context: EventContext, *, arg1: Optional[int] = None
) -> List[MockData]:
    logger.info(context, "mock_app_api_get_list.entry_point")
    return [MockData(f"get-{arg1}")]
