"""
Simple Example: Query Something
--------------------------------------------------------------------
Loads Something from disk
"""
from typing import Union, Optional
from datetime import datetime, timezone

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_extra_logger
from hopeit.toolkit.storage.fs import FileStorage
from model import Something, StatusType, Status, SomethingNotFound

__steps__ = ['load', 'update_status_history']

__api__ = event_api(
    summary="Simple Example: Query Something",
    query_args=[
        ('item_id', str, 'Item Id to read')
    ],
    responses={
        200: (Something, "Something object returned when found"),
        404: (SomethingNotFound, "Information about not found object")
    }
)

logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


async def load(payload: None, context: EventContext, *,
               item_id: str, update_status: bool = False) -> Union[Something, SomethingNotFound]:
    """
    Loads json file from filesystem as `Something` instance

    :param payload: unused
    :param context: EventContext
    :param item_id: str, item id to load
    :return: Loaded `Something` object or SomethingNotFound if not found or validation fails

    """
    assert fs
    logger.info(context, "load", extra=extra(something_id=item_id, path=fs.path))
    something = await fs.get(key=item_id, datatype=Something)
    if something is None:
        logger.warning(context, "item not found", extra=extra(something_id=item_id, path=fs.path))
        return SomethingNotFound(str(fs.path), item_id)
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
