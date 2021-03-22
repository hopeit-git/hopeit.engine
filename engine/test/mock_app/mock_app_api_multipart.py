"""
Test app api multipart post form
"""
from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import BinaryAttachment

__steps__ = ['entry_point']

from mock_app import MockData

logger, extra = app_extra_logger()

__api__ = event_api(
    description="Description Test app api part 2",
    fields=([('field1', str, "Field 1"), ('field2', str, "Field 2"), ('file', BinaryAttachment, "Upload file")]),
    query_args=[('arg1', str, "Argument 1")],
    responses={
        200: int
    }
)


async def __preprocess__(payload: None, context: EventContext, request: PreprocessHook) -> MockData:
    return MockData(value='-'.join(request.parsed_args()))


def entry_point(payload: MockData, context: EventContext, arg1: str) -> int:
    logger.info(context, "mock_app_api_multipart.entry_point")
    return len(payload.value) + len(arg1)
