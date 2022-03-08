import pytest  # type: ignore

from hopeit.dataobjects import copy_payload
from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

from hopeit.fs_storage.partition import get_partition_key

from simple_example.shuffle.spawn_event import SomethingStored

APP_VERSION = APPS_API_VERSION.replace('.', "x")


@pytest.mark.asyncio
async def test_spawn_event(monkeypatch, app_config,  # noqa: F811
                           something_with_status_processed_example, something_with_status_example):  # noqa: F811
    results, msg, response = await execute_event(
        app_config=app_config,
        event_name='shuffle.spawn_event',
        payload=something_with_status_example,
        postprocess=True)
    expected = [copy_payload(something_with_status_processed_example) for _ in range(3)]
    for i, result in enumerate(results):
        expected[i].id = str(i)
        expected[i].status.ts = result.payload.status.ts
        for j in range(len(expected[i].history)):
            expected[i].history[j].ts = result.payload.history[j].ts
        partition_key = get_partition_key(result, "%Y/%m/%d/%H")
        assert result == SomethingStored(
            path=(
                f"{app_config.env['storage']['base_path']}simple_example.{APP_VERSION}.fs_storage.path/"
                f"{partition_key}{result.payload.id}.json"
            ),
            payload=expected[i]
        )
    assert msg == f"events submitted to stream: {app_config.events['shuffle.spawn_event'].write_stream.name}"
    assert response.headers.get("X-Stream-Name") == app_config.events['shuffle.spawn_event'].write_stream.name
    assert len(results) == len(expected)
