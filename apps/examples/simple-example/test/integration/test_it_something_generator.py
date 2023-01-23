import pytest  # type: ignore

from hopeit.testing.apps import execute_event, execute_service
from model import Something, User


@pytest.mark.asyncio
async def test_it_something_generator(app_config, something_params_example):  # noqa: F811
    result = await execute_event(app_config=app_config,
                                 event_name='service.something_generator',
                                 payload=something_params_example)
    assert result == Something(id=something_params_example.id,
                               user=User(id=something_params_example.user, name=something_params_example.user))


@pytest.mark.asyncio
async def test_it_something_generator_service(app_config, something_params_example):  # noqa: F811
    results = await execute_service(app_config=app_config,
                                    event_name='service.something_generator',
                                    max_events=2)
    assert results == [
        Something(id='id1', user=User(id='user1', name='user1'), status=None, history=[]),
        Something(id='id2', user=User(id='user2', name='user2'), status=None, history=[]),
    ]
