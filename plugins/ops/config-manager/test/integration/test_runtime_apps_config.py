import pytest

from hopeit.server import runtime
from hopeit.testing.apps import config, execute_event

from . import MockServer


@pytest.mark.asyncio
async def test_runtime_apps_config(monkeypatch, runtime_apps_response):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config)
    )

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    result = await execute_event(app_config=plugin_config, event_name="runtime-apps-config", payload=None)
    assert result == runtime_apps_response
