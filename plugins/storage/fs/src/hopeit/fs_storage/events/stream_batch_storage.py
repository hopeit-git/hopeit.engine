"""
Stream Batch Storage

This event implementation allows saving data from a stream to the file system.
This event acts as a STREAM event and at the same time as a SERVICE,
managed internally by hopeit.engine once configured (see example below).

The STREAM event, consumed elements from a stream and keeps them in a memory buffer.
The SERVICE part provides a loop to flush the buffer in a fixed time interval.

Example app config:
```
{
  ...
  "settings": {
    "storage.save_events_fs": {
      "path": "/tmp/{auto}",
      "partition_dateformat": "%Y/%m/%d/%H/",
      "flush_seconds": 60.0,
      "flush_max_size": 100
    }
  },
  "events": {
    "storage.save_events_fs": {
      "type": "STREAM",
      "read_stream": {
        "name": "data_stream",
        "consumer_group": "{auto}",
      },
      "impl": "hopeit.fs_storage.events.stream_batch_storage",
      "dataobjects": [
        "model.Something"
      ]
    }
  }
```

This implementation will buffer a number of events for a given time, divided into partitions.
Partitions are determined by the `event_ts()` returning function of a dataobject, i.e.:
```
@dataobject(event_ts='date_field')
@dataclass
class Something:
    ...
    date_field: datetime
    ...
```

If event_ts is not set or date field is None, current timestamp at the moment the event
is consumed in UTC will be used. In case event_ts is defined, it will be converted to UTC
before used for partitioning. In case datetime field is naive (no timezone) it will
be assumed to be in local timezone before converstion to UTC (Python `astimezone()` implementation)

The maximum elements per partition to be kept in memory are set by the `flush_max_size` setting.
The approximate regular interval to flush all partitions in buffer is set by `flush_seconds` setting.
When flushing buffered items, this event implementation will create a folder
per each partition, using the `partition_dateformat` string to create subfolders x time intervals:

i.e. for a daily format `%Y/%m/%d` (default):
```
/save_path/
 |--2022
     |-- 03
          |--01
          |  |-- 55d6f2d4-865d-47a5-8cd3-bf04f7ac07f5.jsonlines
          |  |-- 6d926417-6b16-49ad-86bd-897cbbeaa614.jsonlines
          |  ...
          |--02
             ...
```

This way data can be filtered out on retrieval without the need to iterate
all folders.

Each generated files is a in `jsonlines` format (http://jsonlines.org) where
each line is a valid single-line json object resulting of serializing the
dataobjects consumed from the input stream.
"""

import asyncio
import dataclasses
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from hopeit.app.context import EventContext
from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects import DataObject, dataclass, dataobject
from hopeit.dataobjects.payload import Payload
from hopeit.fs_storage import FileStorageSettings
from hopeit.fs_storage.partition import get_partition_key

logger, extra = app_extra_logger()

__steps__ = ["buffer_item", "flush"]


@dataclasses.dataclass
class Partition:
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)
    items: List[DataObject] = dataclasses.field(default_factory=list)  # type: ignore


SUFFIX = ".jsonlines"
buffer: Dict[str, Partition] = {}
buffer_lock: asyncio.Lock = asyncio.Lock()


@dataobject
@dataclass
class FlushSignal:
    partition_key: str


async def __service__(context: EventContext) -> Spawn[FlushSignal]:
    settings: FileStorageSettings = context.settings(datatype=FileStorageSettings)
    if settings.flush_seconds:
        while True:
            await asyncio.sleep(settings.flush_seconds)
            for partition_key in list(buffer.keys()):
                yield FlushSignal(partition_key=partition_key)
    else:
        if settings.flush_max_size == 0:
            logger.warning(
                context,
                "Flushing partitions by size and time are disabled."
                "Specify either `flush_seconds` or `flush_max_size`"
                "to enable flushing the buffer periodically",
            )
        else:
            logger.info(context, "Flushing partitions by time disabled.")


async def buffer_item(payload: DataObject, context: EventContext) -> Optional[FlushSignal]:
    """
    Consumes any Dataobject type from stream and put it local memory buffer to be flushed later
    """
    settings: FileStorageSettings = context.settings(datatype=FileStorageSettings)
    partition_key = get_partition_key(payload, settings.partition_dateformat or "")
    async with buffer_lock:
        partition = buffer.get(partition_key, Partition())
        buffer[partition_key] = partition
    async with partition.lock:
        partition.items.append(payload)
    if settings.flush_max_size and len(partition.items) >= settings.flush_max_size:
        return FlushSignal(partition_key=partition_key)
    return None


async def flush(signal: FlushSignal, context: EventContext):
    logger.info(context, f"Flushing partition {signal.partition_key}...")
    partition = buffer[signal.partition_key]
    async with partition.lock:
        if len(partition.items):
            await _save_partition(signal.partition_key, partition.items, context)
        async with buffer_lock:
            del buffer[signal.partition_key]
    logger.info(context, f"Flush {signal.partition_key} done.")


async def _save_partition(partition_key: str, items: List[DataObject], context: EventContext):
    settings = context.settings(datatype=FileStorageSettings)
    path = Path(settings.path) / partition_key
    file = path / f"{uuid.uuid4()}{SUFFIX}"
    logger.info(context, f"Saving {file}...")
    os.makedirs(path.resolve(), exist_ok=True)
    async with aiofiles.open(file, "w") as f:
        for item in items:
            await f.write(Payload.to_json(item) + "\n")
