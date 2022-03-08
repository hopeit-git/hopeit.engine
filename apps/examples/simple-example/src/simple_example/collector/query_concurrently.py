"""
Simple Example: Query Concurrently
---------------------------------------------------------------------------
Loads 2 Something objects concurrently from disk and combine the results
using `collector` steps constructor (instantiating an `AsyncCollector`)
"""
import asyncio
from typing import Union, Optional, List

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.events import collector_step
from hopeit.app.logger import app_extra_logger
from hopeit.server.collector import Collector
from hopeit.fs_storage import FileStorage, FileStorageSettings
from model import ItemsInfo, Something, SomethingNotFound


__steps__ = [collector_step(payload=ItemsInfo).gather('load_first', 'load_second', 'combine'), 'result']

__api__ = event_api(
    summary="Simple Example: Query Concurrently",
    payload=(ItemsInfo, "Items to read concurrently"),
    responses={
        200: (List[Something], "List of one or two Something objects returned found, empty list if none is found"),
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


async def load_first(collector: Collector, context: EventContext) -> Union[Something, SomethingNotFound]:
    """
    Loads json file from filesystem as `Something` instance

    :param collector: Collector with payload
    :param context: EventContext
    :return: Loaded `Something` object or SomethingNotFound if not found or validation fails

    """
    assert fs
    items_to_read = await collector['payload']
    item_id = items_to_read.item1_id
    await asyncio.sleep(0.1)
    logger.info(context, "load_second", extra=extra(something_id=item_id, path=fs.path))
    something = await fs.get(key=item_id, datatype=Something, partition_key=items_to_read.partition_key)
    if something is None:
        logger.warning(context, "item not found", extra=extra(something_id=item_id, path=fs.path))
        return SomethingNotFound(str(fs.path), item_id)
    return something


async def load_second(collector: Collector, context: EventContext) -> Union[Something, SomethingNotFound]:
    """
    Loads json file from filesystem as `Something` instance

    :param collector: collector with payload
    :param context: EventContext
    :return: Loaded `Something` object or SomethingNotFound if not found or validation fails

    """
    assert fs
    items_to_read = await collector['payload']
    item_id = items_to_read.item2_id
    await asyncio.sleep(0.1)
    logger.info(context, "load_first", extra=extra(something_id=item_id, path=fs.path))
    something = await fs.get(key=item_id, datatype=Something, partition_key=items_to_read.partition_key)
    if something is None:
        logger.warning(context, "item not found", extra=extra(something_id=item_id, path=fs.path))
        return SomethingNotFound(str(fs.path), item_id)
    return something


async def combine(collector: Collector, context: EventContext) -> List[Something]:
    """
    Awaits for first and second items to be loaded an combine results in list
    if the objects are found. This step combines the results of load_first
    and load_second step that can be executed concurrently by the collector.

    :param collector: collector with load_fist and load_second items
    :param context: EventContext
    :return: List of one or two found Something objects, or emtpy list if non found
    """
    item1 = await collector['load_first']
    item2 = await collector['load_second']
    results = []
    if isinstance(item1, Something):
        results.append(item1)
    if isinstance(item2, Something):
        results.append(item2)
    return results


async def result(collector: Collector, context: EventContext) -> List[Something]:
    items = await collector['combine']
    logger.info(context, f"Found {len(items)} items.")
    return items
