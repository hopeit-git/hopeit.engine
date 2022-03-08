"""
Simple Example: List Objects
--------------------------------------------------------------------
Lists all available Something objects
"""
from typing import Optional, List

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.fs_storage import FileStorage, FileStorageSettings
from model import Something

__steps__ = ['load_all']

__api__ = event_api(
    summary="Simple Example: List Objects",
    query_args=[
        ('wildcard', Optional[str], "Wildcard to filter objects by name")
    ],
    responses={
        200: List[Something]
    }
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


async def load_all(payload: None, context: EventContext, wildcard: str = '*') -> List[Something]:
    """
    Load objects that match the given wildcard
    """
    assert fs
    logger.info(context, "load_all", extra=extra(path=fs.path))
    items: List[Something] = []
    for item_loc in await fs.list_objects(wildcard):
        something = await fs.get(
            key=item_loc.item_id, datatype=Something, partition_key=item_loc.partition_key
        )
        if something is not None:
            items.append(something)
        else:
            logger.warning(context, "Item not found", extra=extra(
                path=fs.path,
                partition_key=item_loc.partition_key,
                item_id=item_loc.item_id
            ))
    return items
