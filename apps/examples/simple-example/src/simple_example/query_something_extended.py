"""
Simple Example: Query Something Extended
--------------------------------------------------------------------
Loads Something from disk, update status base on POST body.
Objects is saved with updated status and history.
"""

from typing import Union, Optional

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_extra_logger
from hopeit.fs_storage import FileStorage, FileStorageSettings
from common.validation import validate
from model import Something, Status, SomethingNotFound

__steps__ = ["load", "save_with_updated_status"]

__api__ = event_api(
    summary="Simple Example: Query Something Extended",
    query_args=[
        ("item_id", str, "Item Id to read"),
        ("partition_key", str, "Partition folder in `YYYY/MM/DD/HH` format"),
    ],
    payload=(Status, "Status change for the retrieved object"),
    responses={
        200: (Something, "Something object returned when found"),
        404: (SomethingNotFound, "Information about not found object"),
    },
)

logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        settings: FileStorageSettings = context.settings(
            key="fs_storage", datatype=FileStorageSettings
        )
        fs = FileStorage.with_settings(settings)


async def load(
    payload: Status,
    context: EventContext,
    *,
    item_id: str,
    partition_key: str,
    update_status: bool = False,
) -> Union[Something, SomethingNotFound]:
    """
    Loads json file from filesystem as `Something` instance,
    sets status to specified payload

    :param payload: Status, status change for the retrieved object
    :param context: EventContext
    :param item_id: str, item id to load
    :return: Loaded `Something` object or SomethingNotFound if not found or validation fails

    """
    assert fs
    logger.info(context, "load", extra=extra(something_id=item_id, path=fs.path))
    something = await fs.get(key=item_id, datatype=Something, partition_key=partition_key)
    if something is None:
        logger.warning(context, "item not found", extra=extra(something_id=item_id, path=fs.path))
        return SomethingNotFound(str(fs.path / partition_key), item_id)
    if something.status and (something.status not in something.history):
        something.history.append(something.status)
    something.status = payload
    return something


async def save_with_updated_status(payload: Something, context: EventContext) -> Something:
    """
    Attempts to validate `payload` and save it to disk in json format

    :param payload: Something object
    :param context: EventContext
    """
    assert fs
    logger.info(context, "validating", extra=extra(something_id=payload.id))
    validate(payload, context=context)
    logger.info(context, "saving", extra=extra(something_id=payload.id, path=fs.path))
    await fs.store(payload.id, payload)
    return payload


async def __postprocess__(
    payload: Union[Something, SomethingNotFound], context: EventContext, response: PostprocessHook
) -> Union[Something, SomethingNotFound]:
    if isinstance(payload, SomethingNotFound):
        logger.debug(context, "404 - File %s not found", payload.id)
        response.status = 404
    return payload
