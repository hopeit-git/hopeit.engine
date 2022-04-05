from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook, PreprocessHook

from . import MockData

__steps__ = ['entry_point']

logger, extra = app_extra_logger()
initialized = False


async def __init_event__(context: EventContext):
    global initialized
    logger.info(context, "INIT")
    initialized = True


async def __preprocess__(payload: MockData, context: EventContext, request: PreprocessHook,
                         *, query_arg1: str) -> MockData:
    assert isinstance(payload, MockData)
    assert request.payload_raw == b'{"value": "ok"}'
    return MockData(value=request.headers.get('X-Track-Request-Id'))


async def entry_point(payload: MockData, context: EventContext, *, query_arg1: str) -> MockData:
    logger.info(context, "mock_post_event.entry_point", extra=extra(query_arg1=query_arg1))
    assert initialized
    return MockData(value=f'{query_arg1}: {payload.value}')


async def __postprocess__(payload: MockData, context: EventContext, response: PostprocessHook) -> MockData:
    response.set_header('recognized', payload.value)
    return payload
