import os
from typing import Any
import pytest

from hopeit.server import config as server_config, version
from hopeit.testing.apps import config


@pytest.fixture
def client_app_config(monkeypatch):

    def mock_getenv(var: str) -> Any:
        if var == "HOPEIT_SIMPLE_EXAMPLE_HOSTS":
            return "test-host"
        if var == "HOPEIT_APPS_API_VERSION":
            return version.APPS_API_VERSION
        if var == "HOPEIT_APPS_ROUTE_VERSION":
            return version.APPS_ROUTE_VERSION
        raise NotImplementedError(var)

    monkeypatch.setattr(server_config.os, "getenv", mock_getenv)
    return config('apps/examples/client-example/config/app-config.json')
