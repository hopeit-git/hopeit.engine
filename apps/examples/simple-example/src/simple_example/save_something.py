"""
Simple Example: Save Something
--------------------------------------------------------------------
Creates and saves Something
"""
from functools import partial
from typing import Optional, Union
import inspect

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.fs_storage import FileStorage, FileStorageSettings
from hopeit.testing.apps import create_test_context

from model import Something, User, SomethingParams
from common.validation import validate

from fastapi import APIRouter

api = APIRouter()

logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None

__steps__ = ["create_something", "save"]


def steps(*steps):
    def wrap(func):
        print("Register events with engine steps", steps)
        f = partial(wrapper, steps)
        f.__doc__ = func.__doc__
        f.__name__ = func.__name__
        module = inspect.getmodule(func)
        setattr(module, "__steps__", steps)
        return f
    return wrap


def wrapper(steps, payload: SomethingParams) -> str:
    print("Executing steps", steps)
    return "PEPE"


def post(**kwargs):
    def wrap(func):
        return api.post("/" + func.__name__, **kwargs)(func)
    return wrap


@post()
@steps("create_something", "save")
async def xxx(payload: SomethingParams) -> str:
    """Creo que esto documenta"""


async def __init_event__(context):
    global fs
    if fs is None:
        settings: FileStorageSettings = context.settings(
            key="fs_storage", datatype=FileStorageSettings
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
