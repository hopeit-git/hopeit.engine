"""
Simple Example: List Objects
--------------------------------------------------------------------
Lists all available Something objects
"""
from typing import Optional, List

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.toolkit.storage.fs import FileStorage
from model import Something

__steps__ = ['load_all']

__api__ = event_api(
    title="Simple Example: List Objects",
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
        fs = FileStorage(path=str(context.env['fs']['data_path']))


async def load_all(payload: None, context: EventContext, wildcard: str = '*') -> List[Something]:
    assert fs
    logger.info(context, "load_all", extra=extra(path=fs.path))
    items: List[Something] = []
    for item_id in await fs.list_objects(wildcard):
        something = await fs.get(key=item_id, datatype=Something)
        if something is not None:
            items.append(something)
    return items
