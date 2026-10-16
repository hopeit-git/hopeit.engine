"""
Test app api query args

Description of Test app queryargs
"""

from datetime import date, datetime

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from mock_app import MockData

logger, extra = app_extra_logger()

__steps__ = ["entry_point"]

__api__ = event_api(
    summary="Test app api query args",
    description="Description of Test app queryargs",
    query_args=[
        ("arg_str", str | None, "str argument"),
        ("arg_int", int | None, "int argument"),
        ("arg_float", float | None, "float argument"),
        ("arg_date", date | None, "date argument"),
        ("arg_datetime", datetime | None, "datetime argument"),
    ],
    responses={200: (list[MockData], "MockData result")},
)


def entry_point(
    payload: None,
    context: EventContext,
    *,
    arg_str: str | None = None,
    arg_int: int | None = None,
    arg_float: float | None = None,
    arg_date: date | None = None,
    arg_datetime: datetime | None = None,
) -> list[MockData]:
    logger.info(context, "mock_app_api_query_args.entry_point")
    return [
        MockData(f"get-{arg_str} get-{arg_int}, get-{arg_float}, get-{arg_date}, get{arg_datetime}")
    ]
