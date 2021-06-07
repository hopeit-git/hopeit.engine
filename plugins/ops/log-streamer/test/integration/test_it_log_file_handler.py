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

    await asyncio.sleep(2)
    lines = await handler.get_and_reset_batch()
    assert len(lines) == 2
    assert lines[0] == raw_log_entries.data[0] + '\n'
    assert lines[1] == raw_log_entries.data[-1] + '\n'

    observer.stop()
    observer.join()

    handler = LogFileHandler(log_config, context)
    observer = start_observer(handler, log_config.logs_path)

    with open(path, 'w') as f:
        for line in raw_log_entries2.data:
            f.write(line + '\n')
    
    await asyncio.sleep(2)
    lines = await handler.get_and_reset_batch()
    assert len(lines) == 2
    assert lines[0] == raw_log_entries2.data[0] + '\n'
    assert lines[1] == raw_log_entries2.data[-1] + '\n'

    await asyncio.sleep(1)
    observer.stop()
    observer.join()
