import pytest  # type: ignore

from hopeit.testing.apps import execute_event

from .fixtures import app_config  # noqa: F401
from .fixtures import something_submitted, something_example  # noqa: F401
from .fixtures import something_with_status_submitted_example  # noqa: F401
from .fixtures import something_with_status_example  # noqa: F401


@pytest.mark.asyncio
async def test_it_process_something(app_config,  # noqa: F811
                                    something_submitted, something_example):  # noqa: F811
    result = await execute_event(app_config=app_config,
                                 event_name='streams.something_event',
                                 payload=something_example)
    something_submitted.status.ts = result.status.ts
    assert result == something_submitted


@pytest.mark.asyncio
async def test_it_process_something_check_history(app_config,  # noqa: F811
                                                  something_with_status_submitted_example,  # noqa: F811
                                                  something_with_status_example):  # noqa: F811, E501
    result = await execute_event(app_config=app_config,
                                 event_name='streams.something_event',
                                 payload=something_with_status_example)
    something_with_status_submitted_example.status.ts = result.status.ts
    something_with_status_submitted_example.history[-1].ts = result.history[-1].ts
    assert result == something_with_status_submitted_example
