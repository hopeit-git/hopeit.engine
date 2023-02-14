"""
Simple Example: Save Something
--------------------------------------------------------------------
Creates and saves Something
"""
from functools import partial
from typing import Optional, Union, Callable
import inspect
from contextvars import ContextVar

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import EventPayload
from hopeit.dataobjects.payload import Payload
from hopeit.fs_storage import FileStorage, FileStorageSettings
from hopeit.testing.apps import create_test_context

from model import Something, User, SomethingParams
from common.validation import validate

from hopeit.app.events import api, steps

logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None

__steps__ = ["create_something", "save"]


@steps("create_something", "save")
async def handler(payload: SomethingParams) -> str:
    """Creo que esto documenta"""
    print("esto")
    return "ESTO"


async def __init_event__(context):
    global fs
    if fs is None:
        # settings: FileStorageSettings = context.settings(
        #     key="fs_storage", datatype=FileStorageSettings
        # )
        settings = FileStorageSettings(
            path="/tmp"
        )
        fs = FileStorage.with_settings(settings)


# pylint: disable=invalid-name
async def __preprocess__(payload: SomethingParams, context: EventContext,
                         request: PreprocessHook) -> Union[str, SomethingParams]:
    user_agent = request.headers.get('user-agent')
    if (user_agent is None) or (user_agent.strip() == ''):
        logger.info(context, "Missing required user-agent")
        request.set_status(400)
        return "Missing required user-agent"

    # logger.info(context, "Save request", extra=extra(user_agent=user_agent))
    return payload


async def create_something(payload: SomethingParams, context: EventContext) -> Something:
    # logger.info(context, "Creating something...", extra=extra(
    #     payload_id=payload.id, user=payload.user
    # ))
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
    # logger.info(context, "validating", extra=extra(something_id=payload.id))
    validate(payload, context=context)
    # logger.info(context, "saving", extra=extra(something_id=payload.id, path=fs.path))
    return await fs.store(payload.id, payload)
