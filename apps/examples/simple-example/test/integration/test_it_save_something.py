from hopeit.app.context import PreprocessHeaders, PreprocessHook
from multidict import CIMultiDict, CIMultiDictProxy
import pytest  # type: ignore
import json

from hopeit.testing.apps import execute_event


def mock_user_agent_header(module, context, *, preprocess_hook: PreprocessHook):
    preprocess_hook.headers = PreprocessHeaders.from_dict({'user-agent': 'Testing!'})


@pytest.mark.asyncio
async def test_it_save_something(app_config, something_params_example):  # noqa: F811
    result = await execute_event(app_config=app_config,
                                 event_name='save_something',
                                 payload=something_params_example,
                                 preprocess=True,
                                 mocks=[mock_user_agent_header])
    assert result == f"{app_config.env['fs']['data_path']}{something_params_example.id}.json"
    with open(str(result)) as f:
        fields = json.loads(f.read())
        assert fields['id'] == something_params_example.id
        assert fields['user']['name'] == something_params_example.user


@pytest.mark.asyncio
async def test_it_save_something_missing_user_agent(app_config, something_params_example):  # noqa: F811
    result = await execute_event(app_config=app_config,
                                 event_name='save_something',
                                 payload=something_params_example,
                                 preprocess=True)
    assert result == "Missing required user-agent"
