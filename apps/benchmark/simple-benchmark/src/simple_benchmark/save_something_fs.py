"""
Simple Benchmark: Save Something
--------------------------------------------------------------------
Creates and saves Something
"""
from typing import Optional

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from hopeit.fs_storage import FileStorage

from model import Something, User, SomethingParams



__steps__ = ['create_something', 'save']

__api__ = event_api(
    payload=(SomethingParams, "provide `id` and `user` to create Something"),
    responses={
        200: (str, 'path where object is saved')
    }
)


logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None
rnd: int = 0


async def __init_event__(context):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


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
    global rnd
    assert fs
    my_id = payload.id + str(rnd)
    rnd += 1
    logger.info(context, "saving", extra=extra(something_id=my_id, path=fs.path))
    return await fs.store(my_id, payload)
