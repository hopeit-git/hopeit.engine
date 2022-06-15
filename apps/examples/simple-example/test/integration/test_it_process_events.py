import pytest

from hopeit.server.version import APPS_ROUTE_VERSION  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.fs_storage.partition import get_partition_key
from simple_example.streams.process_events import SomethingStored


@pytest.mark.asyncio
async def test_it_process_events(app_config,  # noqa: F811
                                 something_submitted, something_processed):  # noqa: F811
    result: SomethingStored = await execute_event(app_config=app_config,
                                                  event_name='streams.process_events',
                                                  payload=something_submitted)
    something_processed.status.ts = result.payload.status.ts
    something_processed.history[-1].ts = result.payload.history[-1].ts
    partition_key = get_partition_key(something_processed, partition_dateformat="%Y/%m/%d/%H")
    assert result == SomethingStored(
            path=(
                f"{app_config.env['storage']['base_path']}simple_example.{APPS_ROUTE_VERSION}.fs_storage.path/"
                f"{partition_key}{result.payload.id}.json"
            ),
            payload=something_processed
        )
