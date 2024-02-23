import pytest  # type: ignore

from hopeit.testing.apps import execute_event, execute_service
from model import Something, User


@pytest.mark.asyncio
async def test_it_something_generator_with_setup_service(
    app_config, something_params_example
):  # noqa: F811
    results = await execute_event(
        app_config=app_config, event_name="setup_something", payload=None
    )
    results = await execute_service(
        app_config=app_config, event_name="service.something_generator", max_events=2
    )
    assert results == [
        Something(
            id="id1", user=User(id="user1", name="user1"), status=None, history=[]
        ),
        Something(
            id="id2", user=User(id="user2", name="user2"), status=None, history=[]
        ),
    ]


@pytest.mark.asyncio
async def test_it_something_generator(
    app_config, something_params_example
):  # noqa: F811
    result = await execute_event(
        app_config=app_config,
        event_name="service.something_generator",
        payload=something_params_example,
    )
    assert result == Something(
        something_params_example.id,
        User(something_params_example.user, something_params_example.user),
    )


@pytest.mark.asyncio
async def test_it_something_generator_service(app_config, something_params_example):
    with pytest.raises(RuntimeError) as exc_info:
        await execute_service(
            app_config=app_config,
            event_name="service.something_generator",
            max_events=2,
        )
        assert (
            str(exc_info.value) == "Service will not start until run setup_something."
        )
