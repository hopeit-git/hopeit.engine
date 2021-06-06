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
async def test_read_single_line(raw_log_entries):
    app_config = config('plugins/ops/log-streamer/config/plugin-config.json')
    file_name = f"{uuid.uuid4()}.log"
    log_config = LogReaderConfig(
        logs_path="/tmp/test_it_log_file_handler/",
        prefix=file_name,
        checkpoint_path='/tmp/test_it_log_file_handler/log_streamer/checkpoints/',
        file_open_timeout_secs=600,
        file_checkpoint_expire_secs=86400,
        batch_size=100,
        batch_wait_interval_secs=1
    )
    os.makedirs(log_config.logs_path, exist_ok=True)
    context = create_test_context(app_config, "log_reader")    
    handler = LogFileHandler(log_config, context)
    observer = start_observer(handler, log_config.logs_path)
    path = Path(f"{log_config.logs_path}{file_name}")
    with open(path, 'w') as f:
        for line in raw_log_entries.data:
            f.write(line + '\n')
    await asyncio.sleep(2)

    lines = await handler.get_and_reset_batch()

    assert lines[0] == raw_log_entries.data[0] + '\n'
    assert lines[1] == raw_log_entries.data[-1] + '\n'
    assert len(lines) == 2
