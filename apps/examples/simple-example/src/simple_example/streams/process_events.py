"""
Simple Example: Process Events
--------------------------------------------------------------------
Process events submitted by something_event app event
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from hopeit.dataobjects import dataobject
from hopeit.toolkit.storage.fs import FileStorage
from model import Something, Status, StatusType

__steps__ = ['update_status', 'save']


@dataobject
@dataclass
class SomethingStored:
    path: str
    payload: Something


logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


def update_status(payload: Something, context: EventContext) -> Something:
    """
    Updates status of payload to PROCESSED and puts previous status in history.

    :param payload: Something, object
    :param context: EventContext
    """
    logger.info(context, "updating something status", extra=extra(something_id=payload.id))

    if payload.status:
        payload.history.append(payload.status)
    payload.status = Status(
        ts=datetime.now(tz=timezone.utc),
        type=StatusType.PROCESSED
    )
    return payload


async def save(payload: Something, context: EventContext) -> SomethingStored:
    """
    Attempts to validate `payload` and save it to disk in json format

    :param payload: Something object
    :param context: EventContext
    """
    assert fs
    logger.info(context, "save", extra=extra(something_id=payload.id, path=fs.path))
    path = await fs.store(payload.id, payload)
    return SomethingStored(
        path=path,
        payload=payload
    )
