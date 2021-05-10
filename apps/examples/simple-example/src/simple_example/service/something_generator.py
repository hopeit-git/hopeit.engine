"""
Simple Example: Service Something Generator
--------------------------------------------------------------------
Creates and publish Something object every 10 seconds
"""
import asyncio
from typing import Optional
import random

from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from hopeit.fs_storage import FileStorage

from model import Something, User, SomethingParams

__steps__ = ['create_something']

logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None


async def __init_event__(context: EventContext):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


async def __service__(context: EventContext) -> Spawn[SomethingParams]:  # pylint: disable=invalid-name
    i = 1
    while True:
        logger.info(context, f"Generating something event {i}...")
        yield SomethingParams(f"id{i}", f"user{i}")
        i += 1
        await asyncio.sleep(random.random() * 10.0)


async def create_something(payload: SomethingParams, context: EventContext) -> Something:
    logger.info(context, "Creating something...", extra=extra(
        payload_id=payload.id, user=payload.user
    ))
    result = Something(
        id=payload.id,
        user=User(id=payload.user, name=payload.user)
    )
    return result
