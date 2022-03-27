from datetime import timezone
from glob import glob
import asyncio
from hopeit.fs_storage.events.stream_batch_storage import FlushSignal

import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION
from hopeit.dataobjects.payload import Payload

from .conftest import TestObject


@pytest.mark.asyncio
async def test_buffer_objects_and_flush_partitions(app_config, test_objs):  # noqa: F811
    test_save_path = app_config.settings["test_stream_batch_storage"]["path"]
    for test_obj in test_objs:
        result = await execute_event(
            app_config=app_config,
            event_name='test_stream_batch_storage',
            payload=test_obj
        )
        assert result is None

    asyncio.sleep(1)  # Allow aiofiles to save
    saved_objects = {}
    for file_name in glob(f'{test_save_path}/2020/05/01/**/*.jsonlines'):
        with open(file_name) as f:
            for line in f:
                obj = Payload.from_json(line, datatype=TestObject)
                saved_objects[obj.object_id] = obj
    assert len(saved_objects) == len(test_objs)
    for obj in test_objs:
        saved = saved_objects[obj.object_id]
        assert obj == saved


@pytest.mark.asyncio
async def test_buffer_object_and_flush_signal(app_config, test_objs):  # noqa: F811
    test_save_path = app_config.settings["test_stream_batch_storage"]["path"]

    # Buffers single object
    test_obj = test_objs[0]
    result = await execute_event(
        app_config=app_config,
        event_name='test_stream_batch_storage',
        payload=test_obj
    )
    assert result is None

    # Send flush partition signal
    partition_key = test_obj.object_ts.strftime("%Y/%m/%d/%H") + '/'
    signal = FlushSignal(partition_key)
    result = await execute_event(
        app_config=app_config,
        event_name='test_stream_batch_storage',
        payload=signal
    )
    assert result is None

    asyncio.sleep(1)  # Allow aiofiles to save
    saved_objects = {}
    for file_name in glob(f'{test_save_path}/{partition_key}/*.jsonlines'):
        with open(file_name) as f:
            for line in f:
                obj = Payload.from_json(line, datatype=TestObject)
                saved_objects[obj.object_id] = obj
    assert len(saved_objects) == 1
    assert test_obj == saved_objects[test_obj.object_id]
