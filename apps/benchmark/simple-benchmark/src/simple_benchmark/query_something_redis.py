"""
Simple Benchamrck: Query Something
--------------------------------------------------------------------
Loads Something from disk
"""
from random import randrange
from typing import Union, Optional
from datetime import datetime, timezone

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_extra_logger
from hopeit.toolkit.storage.redis import RedisStorage
from model import Something, StatusType, Status, SomethingNotFound

__steps__ = ['load', 'update_status_history']

__api__ = event_api(
    query_args=[
        ('item_id', str, 'Item Id to read')
    ],
    responses={
        200: (Something, "Something object returned when found"),
        404: (SomethingNotFound, "Information about not found object")
    }
)

logger, extra = app_extra_logger()
redis: Optional[RedisStorage] = None


async def __init_event__(context):
    global redis
    if redis is None:
        redis = await RedisStorage().connect(address=str(context.env['redis']['address']))


async def load(payload: None, context: EventContext, *,
               item_id: str, update_status: bool = False) -> Union[Something, SomethingNotFound]:
    """
    Loads json file from redis as `Something` instance

    :param payload: unused
    :param context: EventContext
    :param item_id: str, item id to load
    :return: Loaded `Something` object or None if not found or validation fails

    """
    assert redis
    my_id = item_id + str(randrange(0, 1999))
    logger.info(context, "load", extra=extra(something_id=my_id))
    something = await redis.get(key=my_id, datatype=Something)
    if something is None:
        logger.warning(context, "item not found", extra=extra(something_id=my_id))
        return SomethingNotFound(str('redis'), my_id)
    return something


async def update_status_history(payload: Something, context: EventContext) -> Something:
    if payload.status:
        payload.history.append(payload.status)
    payload.status = Status(
        ts=datetime.now(tz=timezone.utc),
        type=StatusType.LOADED
    )
    return payload


async def __postprocess__(payload: Union[Something, SomethingNotFound],
                          context: EventContext,
                          response: PostprocessHook) -> Union[Something, SomethingNotFound]:
    if isinstance(payload, SomethingNotFound):
        response.status = 404
    return payload
