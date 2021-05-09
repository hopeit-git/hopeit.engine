"""
Simple Example: Save Something
--------------------------------------------------------------------
Creates and saves Something
"""
from typing import Optional, Union

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.fs_storage import FileStorage

from model import Something, User, SomethingParams
from common.validation import validate


__steps__ = ['create_something', 'save']

__api__ = event_api(
    summary="Simple Example: Save Something",
    payload=(SomethingParams, "provide `id` and `user` to create Something"),
    responses={
        200: (str, 'path where object is saved'),
        400: (str, 'bad request reason')
    }
)


logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


# pylint: disable=invalid-name
async def __preprocess__(payload: SomethingParams, context: EventContext,
                         request: PreprocessHook) -> Union[str, SomethingParams]:
    user_agent = request.headers.get('user-agent')
    if (user_agent is None) or (user_agent.strip() == ''):
        logger.info(context, "Missing required user-agent")
        request.set_status(400)
        return "Missing required user-agent"

    logger.info(context, "Save request", extra=extra(user_agent=user_agent))
    return payload


async def create_something(payload: SomethingParams, context: EventContext) -> Something:
    logger.info(context, "Creating something...", extra=extra(
        payload_id=payload.id, user=payload.user
    ))
    result = Something(
        id=payload.id,
        user=User(id=payload.user, name=payload.user)
    )
    return result


async def save(payload: Something, context: EventContext) -> str:
    """
    Attempts to validate `payload` and save it to disk in json format

    :param payload: Something object
    :param context: EventContext
    """
    assert fs
    logger.info(context, "validating", extra=extra(something_id=payload.id))
    validate(payload, context=context)
    logger.info(context, "saving", extra=extra(something_id=payload.id, path=fs.path))
    return await fs.store(payload.id, payload)
