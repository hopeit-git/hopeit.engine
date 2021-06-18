from typing import Dict

from hopeit.app.config import AppConfig
from hopeit.server.version import APPS_API_VERSION, ENGINE_VERSION  # noqa: F401

from hopeit.config_manager import RuntimeApps

APP_VERSION = APPS_API_VERSION.replace('.', 'x')


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
        return MockResponse(self.responses[url])
