import pytest
from hopeit.app.config import EventPlugMode

from hopeit.server import runtime
from hopeit.testing.apps import config, execute_event

from . import MockServer


@pytest.mark.asyncio
async def test_runtime_apps_config(monkeypatch, runtime_apps_response):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    basic_auth_config = config('plugins/auth/basic-auth/config/plugin-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(app_config, basic_auth_config)
    )

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    result = await execute_event(app_config=plugin_config, event_name="runtime_apps_config", payload=None)

    import json    
    assert result == runtime_apps_response


@pytest.mark.asyncio
async def test_runtime_apps_config_expand_events(monkeypatch, effective_events_example):
    app_config = config('apps/examples/simple-example/config/app-config.json')
    basic_auth_config = config('plugins/auth/basic-auth/config/plugin-config.json')
    server = MockServer(app_config, basic_auth_config)
    server.set_effective_events(
        app_config.app_key(), effective_events_example
    )
    monkeypatch.setattr(runtime, "server", server)

    plugin_config = config('plugins/ops/config-manager/config/plugin-config.json')
    result = await execute_event(
        app_config=plugin_config, event_name="runtime_apps_config",
        payload=None, expand_events=True
    )

    app_prefix = app_config.app_key()
    for k, v in result.apps[app_config.app_key()].effective_events.items():
        assert k[0: len(app_prefix)] == app_prefix
        if v.plug_mode == EventPlugMode.ON_APP:
            app_plugin_prefx = f"{app_prefix}.{basic_auth_config.app_key()}"
            assert k[0: len(app_plugin_prefx)] == app_plugin_prefx
        event_name = k.split('.')[-1]
        assert v == effective_events_example[event_name]
