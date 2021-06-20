from hopeit.app.config import AppConfig


class MockAppEngine:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config


class MockServer:
    def __init__(self, *app_config: AppConfig):
        self.app_engines = {
            cfg.app_key(): MockAppEngine(cfg)
            for cfg in app_config
        }
