"""
Simple Example: Service Something Generator
--------------------------------------------------------------------
Creates and publish Something object every 10 seconds
"""
import asyncio
import random

from hopeit.app.context import EventContext
from hopeit.app.events import Spawn, service_running
from hopeit.app.logger import app_extra_logger

from model import Something, User, SomethingParams

__steps__ = ['create_something']

logger, extra = app_extra_logger()


async def __service__(context: EventContext) -> Spawn[SomethingParams]:
    i = 1
    while service_running(context):
        logger.info(context, f"Generating something event {i}...")
        yield SomethingParams(f"id{i}", f"user{i}")
        i += 1
        await asyncio.sleep(random.random() * 10.0)
    logger.info(context, "Service seamlessly exit")


async def create_something(payload: SomethingParams, context: EventContext) -> Something:
    logger.info(context, "Creating something...", extra=extra(
        payload_id=payload.id, user=payload.user
    ))
    result = Something(
        id=payload.id,
        user=User(id=payload.user, name=payload.user)
    )
    await asyncio.sleep(random.random() * 5.0)
    return result
