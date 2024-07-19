from hopeit.apps_client import AppsClientSettings, ClientAuthStrategy
import pytest

from hopeit.app.config import (
    AppConfig,
    AppConnection,
    AppDescriptor,
    AppEngineConfig,
    EventConnection,
    EventConnectionType,
    EventDescriptor,
    EventType,
)
from hopeit.dataobjects.payload import Payload
from hopeit.server.config import LoggingConfig, ServerConfig
from hopeit.server.version import APPS_API_VERSION


@pytest.fixture
def mock_client_app_config():
    return AppConfig(
        app=AppDescriptor(name="mock_client_app", version="test"),
        engine=AppEngineConfig(import_modules=["mock_client_app"]),
        app_connections={
            "test_app_connection": AppConnection(
                name="test_app", version=APPS_API_VERSION, client="hopeit.apps_client.AppsClient"
            ),
            "test_app_plugin_connection": AppConnection(
                name="test_app",
                version=APPS_API_VERSION,
                client="hopeit.apps_client.AppsClient",
                plugin_name="test_plugin",
                plugin_version=APPS_API_VERSION,
            ),
            "test_app_plugin_unsecured": AppConnection(
                name="test_app",
                version=APPS_API_VERSION,
                client="hopeit.apps_client.AppsClient",
                plugin_name="test_plugin",
                plugin_version=APPS_API_VERSION,
            ),
        },
        settings={
            "test_app_connection": Payload.to_obj(
                AppsClientSettings(connection_str="http://test-host1,http://test-host2")
            ),
            "test_app_plugin_connection": Payload.to_obj(
                AppsClientSettings(
                    connection_str="http://test-host1,http://test-host2",
                    auth_strategy=ClientAuthStrategy.FORWARD_CONTEXT,
                )
            ),
            "test_app_plugin_unsecured": Payload.to_obj(
                AppsClientSettings(
                    connection_str="http://test-host1,http://test-host2",
                    auth_strategy=ClientAuthStrategy.UNSECURED,
                )
            ),
        },
        events={
            "mock_client_event": EventDescriptor(
                type=EventType.GET,
                connections=[
                    EventConnection(
                        app_connection="test_app_connection",
                        event="test_event_get",
                        type=EventConnectionType.GET,
                    ),
                    EventConnection(
                        app_connection="test_app_connection",
                        event="test_event_post",
                        type=EventConnectionType.POST,
                    ),
                    EventConnection(
                        app_connection="test_app_plugin_connection",
                        event="test_event_plugin",
                        type=EventConnectionType.GET,
                    ),
                    EventConnection(
                        app_connection="test_app_plugin_unsecured",
                        event="test_event_plugin",
                        type=EventConnectionType.GET,
                    ),
                ],
            )
        },
        server=ServerConfig(logging=LoggingConfig(log_level="DEBUG", log_path="work/logs/test/")),
    ).setup()


@pytest.fixture
def mock_auth(mocker):
    auth_mock = mocker.MagicMock()
    auth_mock.new_token = mocker.MagicMock()
    auth_mock.new_token.return_value = "test-token"
    return auth_mock
