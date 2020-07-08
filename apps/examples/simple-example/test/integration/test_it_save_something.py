import pytest  # type: ignore
import json

from hopeit.testing.apps import execute_event
from .fixtures import app_config  # noqa: F401
from .fixtures import something_example, something_params_example  # noqa: F401


@pytest.mark.asyncio
async def test_it_save_something(app_config, something_params_example):  # noqa: F811
    result = await execute_event(app_config=app_config,
                                 event_name='save_something',
                                 payload=something_params_example)
    assert result == f"{app_config.env['fs']['data_path']}{something_params_example.id}.json"
    with open(str(result)) as f:
        fields = json.loads(f.read())
        assert fields['id'] == something_params_example.id
        assert fields['user']['name'] == something_params_example.user
