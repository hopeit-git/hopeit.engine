"""
Test app noapi
"""
from typing import Optional

from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from mock_app import MockData   # type: ignore

logger, extra = app_extra_logger()

__steps__ = ['entry_point']


def entry_point(payload: None, context: EventContext, arg1: Optional[int] = None) -> MockData:
    logger.info(context, "mock_app_noapi.entry_point")
    return MockData(f"get-{arg1}")
