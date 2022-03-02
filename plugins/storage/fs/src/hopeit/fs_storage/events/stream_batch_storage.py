import asyncio
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from hopeit.app.context import EventContext
from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects import DataObject, dataobject
from hopeit.dataobjects.payload import Payload
from hopeit.fs_storage import FileStorageSettings

logger, extra = app_extra_logger()

__steps__ = ['buffer_item', 'flush']


@dataclass
class Partition:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    items: List[DataObject] = field(default_factory=list)

buffer: Dict[str, Partition] = {}


@dataobject
@dataclass
class FlushSignal:
    partition_key: str


async def __service__(context: EventContext) -> Spawn[FlushSignal]:
    global buffer
    while True:
        await asyncio.sleep(60.0)
        for partition_key in list(buffer.keys()):
            yield FlushSignal(partition_key=partition_key)


async def buffer_item(payload: DataObject, context: EventContext) -> Optional[FlushSignal]:
    global buffer
    ts = payload.event_ts() or datetime.now()
    partition_key = ts.strftime("%Y/%m/%d/")
    partition = buffer.get(partition_key, Partition())
    async with partition.lock:
        partition.items.append(payload)
    buffer[partition_key] = partition
    # if len(partition.items) >= 10:
    #     return FlushSignal(partition_key=partition_key)
    return None


async def flush(signal: FlushSignal, context: EventContext):
    global buffer
    logger.info(context, f"Flushing partition {signal.partition_key}...")
    partition = buffer[signal.partition_key]
    async with partition.lock:
        if len(partition.items):
            await _save_partition(signal.partition_key, partition.items, context)
        del buffer[signal.partition_key]
    logger.info(context, f"Flush {signal.partition_key} done.")


async def _save_partition(partition_key: str, items: List[DataObject], context: EventContext):
    settings = context.settings(datatype=FileStorageSettings)
    path = Path(settings.path) / partition_key
    file = path / f"{uuid.uuid4()}.jsonlines"
    logger.info(context, f"Saving {file}...")
    os.makedirs(path.resolve(), exist_ok=True)
    async with aiofiles.open(file, 'w') as f:
        for item in items:
            await f.write(Payload.to_json(item) + "\n")
