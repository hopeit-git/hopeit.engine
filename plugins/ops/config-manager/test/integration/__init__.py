from typing import Dict

from hopeit.app.config import AppConfig

from hopeit.config_manager import RuntimeApps

from hopeit.server.version import APPS_ROUTE_VERSION


class MockAppEngine:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config


class MockServer:
    def __init__(self, *app_config: AppConfig):
        self.app_engines = {
            cfg.app_key(): MockAppEngine(cfg)
            for cfg in app_config
        }


class MockResponse():
    def __init__(self, response: RuntimeApps):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def json(self):
        return self.response.to_dict()


class MockClientSession():

    responses: Dict[str, RuntimeApps] = {}

    @classmethod
    def setup(cls, responses: Dict[str, RuntimeApps]):
        cls.responses = responses
        return cls

    def __init__(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    def get(self, url: str) -> MockResponse:
        if url in self.responses:
            return MockResponse(self.responses[url])
        raise IOError("Test error")


def mock_client(module, monkeypatch, server1_apps_response, server2_apps_response, expand_events=False):
    url_pattern = "{}/api/config-manager/{}/runtime-apps-config?url={}&expand_events={}"
    url1 = url_pattern.format("http://test-server1", APPS_ROUTE_VERSION, "http://test-server1", str(expand_events).lower())
    url2 = url_pattern.format("http://test-server2", APPS_ROUTE_VERSION, "http://test-server2", str(expand_events).lower())
    monkeypatch.setattr(module.aiohttp, 'ClientSession', MockClientSession.setup(
        responses={
            url1: server1_apps_response,
            url2: server2_apps_response
        }
    ))
