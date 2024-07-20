from typing import Dict, Optional

import aiohttp

from hopeit.app.config import AppConfig, EventDescriptor
from hopeit.config_manager import RuntimeApps
from hopeit.dataobjects.payload import Payload
from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.app.context import EventContext
from hopeit.server.events import get_event_settings
from hopeit.server.config import AuthType
from hopeit.testing.apps import config


class MockAppEngine:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config
        self.effective_events: Dict[str, EventDescriptor] = {}


class MockServer:
    def __init__(self, *app_config: AppConfig):
        self.app_engines = {cfg.app_key(): MockAppEngine(cfg) for cfg in app_config}

    def set_effective_events(self, app_key: str, effective_events: Dict[str, EventDescriptor]):
        self.app_engines[app_key].effective_events = effective_events


class MockResponse:
    def __init__(self, response: RuntimeApps):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def json(self):
        return Payload.to_obj(self.response)


class MockClientSession:
    responses: Dict[str, RuntimeApps] = {}
    # timeout: aiohttp.ClientTimeout = aiohttp.ClientTimeout(total=10.0)

    @classmethod
    def setup(cls, responses: Dict[str, RuntimeApps]):
        cls.responses = responses
        return cls

    def __init__(self, timeout: aiohttp.ClientTimeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    def get(self, url: str) -> MockResponse:
        if self.timeout.total is not None and self.timeout.total < 10.0:
            raise TimeoutError()
        if url in self.responses:
            return MockResponse(self.responses[url])
        raise IOError("Test error")


def mock_effective_events(response, effective_events=None):
    if effective_events:
        for _, app_info in response.apps.items():
            app_info.effective_events = effective_events
    return response


def mock_client(
    module, monkeypatch, server1_apps_response, server2_apps_response, effective_events=None
):
    expand_events = str(effective_events is not None).lower()
    url_pattern = "{}/api/config-manager/{}/runtime-apps-config?url={}&expand_events={}"
    url1 = url_pattern.format(
        "http://test-server1",
        APPS_ROUTE_VERSION,
        "http://test-server1",
        str(expand_events).lower(),
    )
    url2 = url_pattern.format(
        "http://test-server2",
        APPS_ROUTE_VERSION,
        "http://test-server2",
        str(expand_events).lower(),
    )
    monkeypatch.setattr(
        module.aiohttp,
        "ClientSession",
        MockClientSession.setup(
            responses={
                url1: mock_effective_events(server1_apps_response, effective_events),
                url2: mock_effective_events(server2_apps_response, effective_events),
            }
        ),
    )


def mock_context(event_name: str, timeout: Optional[float] = None) -> EventContext:
    plugin_config = config("plugins/ops/config-manager/config/plugin-config.json")
    if timeout:
        plugin_config.settings["config_manager_client"]["client_timeout"] = timeout
    event_settings = get_event_settings(plugin_config.effective_settings, event_name)  # type: ignore
    return EventContext(
        app_config=app_config(),
        event_name=event_name,
        plugin_config=plugin_config,
        settings=event_settings,
        track_ids={},
        auth_info={"auth_type": AuthType.UNSECURED, "allowed": "true"},
    )


def app_config() -> AppConfig:
    return config("plugins/ops/config-manager/config/plugin-config.json")
