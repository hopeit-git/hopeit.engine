import pytest
import json

from hopeit.testing.apps import config, create_test_context, execute_event

from hopeit.log_streamer import LogEntry, LogBatch, LogRawBatch

@pytest.mark.asyncio
async def test_log_reader(raw_log_entries, expected_log_entries):
    app_config = config('plugins/ops/log-streamer/config/plugin-config.json')

    result = await execute_event(app_config, "log_reader", raw_log_entries)
    # print(json.dumps(result.to_dict(), indent=2))
    assert result == expected_log_entries

