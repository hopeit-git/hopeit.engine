from hopeit.app.context import PreprocessHeaders, PreprocessHook
from hopeit.fs_storage.partition import get_partition_key
import pytest  # type: ignore
import json

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

APP_VERSION = APPS_API_VERSION.replace(".", "x")


def mock_user_agent_header(module, context, *, preprocess_hook: PreprocessHook):
    preprocess_hook.headers = PreprocessHeaders.from_dict({"user-agent": "Testing!"})


@pytest.mark.asyncio
async def test_it_save_something(app_config, something_params_example):  # noqa: F811
    result = await execute_event(
        app_config=app_config,
        event_name="save_something",
        payload=something_params_example,
        preprocess=True,
        mocks=[mock_user_agent_header],
    )
    partition_key = get_partition_key(something_params_example, "%Y/%m/%d/%H")
    assert result == (
        f"{app_config.env['storage']['base_path']}simple_example.{APP_VERSION}.fs_storage.path/"
        f"{partition_key}{something_params_example.id}.json"
    )
    with open(str(result)) as f:
        fields = json.loads(f.read())
        assert fields["id"] == something_params_example.id
        assert fields["user"]["name"] == something_params_example.user


@pytest.mark.asyncio
async def test_it_save_something_missing_user_agent(app_config, something_params_example):  # noqa: F811
    result = await execute_event(
        app_config=app_config,
        event_name="save_something",
        payload=something_params_example,
        preprocess=True,
    )
    assert result == "Missing required user-agent"
