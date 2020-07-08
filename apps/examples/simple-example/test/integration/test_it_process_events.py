import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from simple_example.streams.process_events import SomethingStored

from .fixtures import app_config  # noqa: F401
from .fixtures import something_processed, something_submitted  # noqa: F401


@pytest.mark.asyncio
async def test_it_process_events(app_config,  # noqa: F811
                                 something_submitted, something_processed):  # noqa: F811
    result: SomethingStored = await execute_event(app_config=app_config,
                                                  event_name='streams.process_events',
                                                  payload=something_submitted)
    something_processed.status.ts = result.payload.status.ts
    something_processed.history[-1].ts = result.payload.history[-1].ts
    assert result == SomethingStored(
            path=f"{app_config.env['fs']['data_path']}{result.payload.id}.json",
            payload=something_processed
        )
