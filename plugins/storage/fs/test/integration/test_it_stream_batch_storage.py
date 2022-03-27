from glob import glob
import asyncio
from hopeit.fs_storage.events.stream_batch_storage import FlushSignal

import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.dataobjects.payload import Payload

from . import MyObject


@pytest.mark.asyncio
async def test_buffer_objects_and_flush_partitions(app_config, test_objs):  # noqa: F811
    test_save_path = app_config.settings["test_stream_batch_storage"]["path"]

    # Buffer 10 objects that should create 5 partitions
    for test_obj in test_objs:
        result = await execute_event(
            app_config=app_config,
            event_name='test_stream_batch_storage',
            payload=test_obj
        )
        assert result is None

    await asyncio.sleep(1)  # Allow aiofiles to save

    # Load saved data from disk and compare to input
    saved_objects = {}
    for file_name in glob(f'{test_save_path}/2020/05/01/**/*.jsonlines'):
        with open(file_name) as f:
            for line in f:
                obj = Payload.from_json(line, datatype=MyObject)
                saved_objects[obj.object_id] = obj
    assert len(saved_objects) == len(test_objs)
    for obj in test_objs:
        saved = saved_objects[obj.object_id]
        assert obj == saved


@pytest.mark.asyncio
async def test_buffer_object_and_flush_signal(app_config, test_objs):  # noqa: F811
    test_save_path = app_config.settings["test_stream_batch_storage"]["path"]

    # Buffer single object
    test_obj = test_objs[0]
    result = await execute_event(
        app_config=app_config,
        event_name='test_stream_batch_storage',
        payload=test_obj
    )
    assert result is None

    # Send flush partition signal to force flush single object
    partition_key = test_obj.object_ts.strftime("%Y/%m/%d/%H") + '/'
    signal = FlushSignal(partition_key)
    result = await execute_event(
        app_config=app_config,
        event_name='test_stream_batch_storage',
        payload=signal
    )
    assert result is None

    # Load saved object and check is correct
    await asyncio.sleep(1)  # Allow aiofiles to save
    saved_objects = {}
    for file_name in glob(f'{test_save_path}/{partition_key}/*.jsonlines'):
        with open(file_name) as f:
            for line in f:
                obj = Payload.from_json(line, datatype=MyObject)
                saved_objects[obj.object_id] = obj
    assert len(saved_objects) == 1
    assert test_obj == saved_objects[test_obj.object_id]
