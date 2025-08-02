from hopeit.dataobjects.payload import Payload

import asyncio
import os
from pathlib import Path

from hopeit.testing.apps import config, execute_event

from hopeit.log_streamer import log_reader


async def test_log_reader(raw_log_entries, expected_log_entries):
    app_config = config("plugins/ops/log-streamer/config/plugin-config.json")
    result = await execute_event(app_config, "log_reader", raw_log_entries)
    assert result == expected_log_entries


async def write_logs(log_config, raw_log_entries):
    os.makedirs(log_config.logs_path, exist_ok=True)
    path = Path(f"{log_config.logs_path}{log_config.prefix}")
    await asyncio.sleep(2)
    with open(path, "w") as f:
        for line in raw_log_entries.data:
            f.write(line + "\n")
        f.flush()


async def test_service(monkeypatch, raw_log_entries, log_config, service_context):
    monkeypatch.setattr(service_context.settings, "extras", {"_": Payload.to_obj(log_config)})
    loop = asyncio.get_event_loop()
    loop.create_task(write_logs(log_config, raw_log_entries))
    lines = []
    async for batch in log_reader.__service__(service_context):
        lines = batch.data
        break

    await asyncio.sleep(2)
    assert len(lines) == 2
    assert lines[0] == raw_log_entries.data[0] + "\n"
    assert lines[1] == raw_log_entries.data[-1] + "\n"
