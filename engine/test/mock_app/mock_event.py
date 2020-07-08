from typing import Union

from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook
from . import MockData

__steps__ = ['entry_point', 'handle_ok_case', 'handle_special_case']

logger, extra = app_extra_logger()

initialized = False


def __init_event__(context: EventContext):
    global initialized
    logger.info(context, "INIT")
    initialized = True


def entry_point(payload: None, context: EventContext, *, query_arg1: str) -> Union[MockData, str]:
    logger.info(context, "mock_event.entry_point", extra=extra(query_arg1=query_arg1))
    assert initialized
    if query_arg1 == 'fail':
        raise AssertionError("Test for error")
    if query_arg1 == 'ok':
        return MockData(value='ok')
    return "None"


async def handle_special_case(payload: str, context: EventContext) -> str:
    assert initialized
    return payload


async def handle_ok_case(payload: MockData, context: EventContext) -> str:
    assert initialized
    return "ok: " + payload.value


async def __postprocess__(payload: str, context: EventContext, response: PostprocessHook) -> str:
    if payload.startswith('ok:'):
        response.set_status(200)
        response.set_header('X-Status', 'ok')
        response.set_cookie('Test-Cookie', 'ok')
        return payload
    response.set_status(400)
    response.del_cookie('Test-Cookie')
    return "not-ok: " + payload
