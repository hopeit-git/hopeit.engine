from typing import Dict
from hopeit.app.config import AppConfig, EventDescriptor
from hopeit.dataobjects.payload import Payload
from hopeit.server.version import APPS_API_VERSION, APPS_ROUTE_VERSION
from hopeit.server import config as server_config
from hopeit.testing.apps import config

from hopeit.config_manager.runtime import runtime
from hopeit.apps_visualizer import apps


class MockAppEngine:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.effective_events: Dict[str, EventDescriptor] = {}


class MockServer:
    def __init__(self, *app_config: AppConfig):
        self.app_engines = {cfg.app_key(): MockAppEngine(cfg) for cfg in app_config}


def mock_getenv(var_name):
    if var_name == "HOPEIT_APPS_VISUALIZER_HOSTS":
        return "in-process"
    if var_name == "HOPEIT_SIMPLE_EXAMPLE_HOSTS":
        return "test-host"
    if var_name == "HOPEIT_APPS_API_VERSION":
        return APPS_API_VERSION
    if var_name == "HOPEIT_APPS_ROUTE_VERSION":
        return APPS_ROUTE_VERSION
    return None


def mock_runtime(monkeypatch, effective_events):
    setattr(apps, "_expire", 0.0)
    monkeypatch.setattr(server_config.os, "getenv", mock_getenv)
    app_config = config("apps/examples/simple-example/config/app-config.json")
    basic_auth_config = config("plugins/auth/basic-auth/config/plugin-config.json")
    client_app_config = config("apps/examples/client-example/config/app-config.json")
    server = MockServer(basic_auth_config, app_config, client_app_config)
    for app_key, app_effective_events in effective_events.items():
        server.app_engines[app_key].effective_events = Payload.from_obj(
            app_effective_events, datatype=Dict[str, EventDescriptor]
        )
    monkeypatch.setattr(runtime, "server", server)
