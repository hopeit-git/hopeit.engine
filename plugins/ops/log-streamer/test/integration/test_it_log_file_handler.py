import pytest

import asyncio
import uuid
import os
import platform
from pathlib import Path
from hopeit.testing.apps import config, create_test_context

from hopeit.log_streamer import LogFileHandler, LogReaderConfig, start_observer


@pytest.mark.asyncio
@pytest.mark.skipif(
    platform.system().lower() != "linux",
    reason="LogFileReader uses watchdog that works with no additional helpers only in Linux"
)
async def test_read_single_line(raw_log_entries, log_config, context):
    handler = LogFileHandler(log_config, context)
    os.makedirs(log_config.logs_path, exist_ok=True)
    observer = start_observer(handler, log_config.logs_path)
    path = Path(f"{log_config.logs_path}{log_config.prefix}")
    with open(path, 'w') as f:
        for line in raw_log_entries.data:
            f.write(line + '\n')
    await asyncio.sleep(2)

    lines = await handler.get_and_reset_batch()

    assert len(lines) == 2
    assert lines[0] == raw_log_entries.data[0] + '\n'
    assert lines[1] == raw_log_entries.data[-1] + '\n'
    
    observer.stop()
    observer.join()


@pytest.mark.asyncio
@pytest.mark.skipif(
    platform.system().lower() != "linux",
    reason="LogFileReader uses watchdog that works with no additional helpers only in Linux"
)
async def test_read_checkpoint(raw_log_entries, raw_log_entries2, log_config, context):
    handler = LogFileHandler(log_config, context)
    os.makedirs(log_config.logs_path, exist_ok=True)
    observer = start_observer(handler, log_config.logs_path)
    path = Path(f"{log_config.logs_path}{log_config.prefix}")
    
    with open(path, 'w') as f:
        for line in raw_log_entries.data:
            f.write(line + '\n')
        f.flush()

        await asyncio.sleep(1)
        lines = await handler.get_and_reset_batch()
        assert len(lines) == 2
        assert lines[0] == raw_log_entries.data[0] + '\n'
        assert lines[1] == raw_log_entries.data[-1] + '\n'

        observer.stop()
        observer.join()

        handler = LogFileHandler(log_config, context)
        observer = start_observer(handler, log_config.logs_path)

        # with open(path, 'a') as f:
        for line in raw_log_entries2.data:
            f.write(line + '\n')
        f.flush()

        await asyncio.sleep(1)
        lines = await handler.get_and_reset_batch()
        assert len(lines) == 2
        assert lines[0] == raw_log_entries2.data[0] + '\n'
        assert lines[1] == raw_log_entries2.data[-1] + '\n'

        await asyncio.sleep(1)

    observer.stop()
    observer.join()


@pytest.mark.asyncio
@pytest.mark.skipif(
    platform.system().lower() != "linux",
    reason="LogFileReader uses watchdog that works with no additional helpers only in Linux"
)
async def test_checkpoint_expire(raw_log_entries, raw_log_entries2, log_config, context):
    log_config.file_checkpoint_expire_secs = 1
    handler = LogFileHandler(log_config, context)
    os.makedirs(log_config.logs_path, exist_ok=True)
    observer = start_observer(handler, log_config.logs_path)
    path = Path(f"{log_config.logs_path}{log_config.prefix}")
    
    with open(path, 'w') as f:
        for line in raw_log_entries.data:
            f.write(line + '\n')
        f.flush()

        await asyncio.sleep(1)
        lines = await handler.get_and_reset_batch()
        assert len(lines) == 2
        assert lines[0] == raw_log_entries.data[0] + '\n'
        assert lines[1] == raw_log_entries.data[-1] + '\n'

        observer.stop()
        observer.join()

        handler = LogFileHandler(log_config, context)
        observer = start_observer(handler, log_config.logs_path)
        await asyncio.sleep(2)

        # with open(path, 'a') as f:
        for line in raw_log_entries2.data:
            f.write(line + '\n')
        f.flush()

        await asyncio.sleep(1)
        lines = await handler.get_and_reset_batch()
        assert len(lines) == 4
        assert lines[0] == raw_log_entries.data[0] + '\n'
        assert lines[1] == raw_log_entries.data[-1] + '\n'
        assert lines[2] == raw_log_entries2.data[0] + '\n'
        assert lines[3] == raw_log_entries2.data[-1] + '\n'

        await asyncio.sleep(1)

    observer.stop()
    observer.join()


@pytest.mark.asyncio
@pytest.mark.skipif(
    platform.system().lower() != "linux",
    reason="LogFileReader uses watchdog that works with no additional helpers only in Linux"
)
async def test_read_checkpoint_same_timestamp(raw_log_entries, raw_log_entries2, log_config, context):
    handler = LogFileHandler(log_config, context)
    os.makedirs(log_config.logs_path, exist_ok=True)
    observer = start_observer(handler, log_config.logs_path)
    path = Path(f"{log_config.logs_path}{log_config.prefix}")
    
    with open(path, 'w') as f:
        for line in raw_log_entries.data:
            f.write(line + '\n')
        special_case = raw_log_entries.data[-1][0:24] + raw_log_entries2.data[0][25:] + '\n'
        f.write(special_case)
        f.flush()

        await asyncio.sleep(1)
        lines = await handler.get_and_reset_batch()
        assert len(lines) == 3
        assert lines[0] == raw_log_entries.data[0] + '\n'
        assert lines[1] == raw_log_entries.data[-1] + '\n'
        assert lines[2] == special_case

        observer.stop()
        observer.join()

        handler = LogFileHandler(log_config, context)
        observer = start_observer(handler, log_config.logs_path)

        # with open(path, 'a') as f:
        f.write(special_case)
        for line in raw_log_entries2.data[1:]:
            f.write(line + '\n')
        f.flush()

        await asyncio.sleep(1)
        lines = await handler.get_and_reset_batch()
        assert len(lines) == 2
        assert lines[0] == special_case
        assert lines[1] == raw_log_entries2.data[-1] + '\n'

        await asyncio.sleep(1)

    observer.stop()
    observer.join()