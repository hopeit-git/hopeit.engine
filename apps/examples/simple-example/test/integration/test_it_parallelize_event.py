import pytest  # type: ignore

from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_parallelize_event(monkeypatch, app_config,  # noqa: F811
                                 something_with_status_processed_example, something_with_status_example):  # noqa: F811
    results, msg, response = await execute_event(
        app_config=app_config,
        event_name='shuffle.parallelize_event',
        payload=something_with_status_example,
        postprocess=True)
    first = something_with_status_processed_example.copy(deep=True)
    first.id = 'first_' + first.id
    second = something_with_status_processed_example.copy(deep=True)
    second.id = 'second_' + second.id
    for i, expected in enumerate([first, second]):
        expected.status.ts = results[i].payload.status.ts
        for j in range(len(expected.history)):
            expected.history[j].ts = results[i].payload.history[j].ts
    assert results[0].path.split('/')[-1] == f"{first.id}.json"
    assert results[0].payload == first
    assert results[1].path.split('/')[-1] == f"{second.id}.json"
    assert results[1].payload == second
    assert msg == f"events submitted to stream: {app_config.events['shuffle.parallelize_event'].write_stream.name}"
    assert response.headers.get("X-Stream-Name") == app_config.events['shuffle.parallelize_event'].write_stream.name
    assert len(results) == 2
