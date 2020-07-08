"""
Simple Benchamrck: Give me Something
--------------------------------------------------------------------
Loads Something from disk
"""
import asyncio
from random import randrange

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from model import Something, User

__steps__ = ['create']

__api__ = event_api(
    query_args=[
        ('item_id', str, 'Item Id to read')
    ],
    responses={
        200: (Something, "Something object returned when found")
    }
)

logger, extra = app_extra_logger()


async def create(payload: None, context: EventContext, *,
                 item_id: str, update_status: bool = False) -> Something:
    """
    Loads json file from filesystem as `Something` instance

    :param payload: unused
    :param context: EventContext
    :param item_id: str, item id to load
    :return: Loaded `Something` object or None if not found or validation fails

    """
    rnd_id = item_id + str(randrange(0, 1999))
    await asyncio.sleep(0.001)
    return Something(
        id=rnd_id,
        user=User(id=rnd_id, name=rnd_id)
    )
