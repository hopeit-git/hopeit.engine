from typing import Any
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.streams.storage import StreamStorageOp, Result

from hopeit.fs_storage import FileStorage, FileStorageSettings

from hopeit.dataobjects import DataObject, EventPayload

logger, extra = app_extra_logger()

__steps__ = ['store']


async def store(payload: DataObject, context: EventContext) -> StreamStorageOp:
    settings = context.settings(datatype=FileStorageSettings)
    logger.info(context, f"Saving item...", extra=extra(
        path=settings.path,
    ))
    info = await FileStorage(path=settings.path).store(key=payload.event_id(), value=payload)
    return StreamStorageOp(
        result=Result.OK,
        info=info
    )
