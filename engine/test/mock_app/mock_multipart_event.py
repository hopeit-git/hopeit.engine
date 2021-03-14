"""
Test multipart post form
"""
from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import BinaryAttachment

__steps__ = ['entry_point']

from mock_app import MockData

logger, extra = app_extra_logger()


async def __preprocess__(payload: None, context: EventContext, request: PreprocessHook) -> MockData:
    fields = await request.parsed_args()
    print("fields", fields)
    print("headers", request.headers)
    return MockData(value=' '.join(f"{k}={v}" for k,v in fields.items()))


def entry_point(payload: MockData, context: EventContext, query_arg1: str) -> MockData:
    logger.info(context, "mock_multipart_event.entry_point")
    return MockData(value=f"{payload.value} {query_arg1}")
