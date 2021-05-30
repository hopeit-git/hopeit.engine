from hopeit.app.config import AppConfig
from hopeit.server.version import APPS_API_VERSION

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
