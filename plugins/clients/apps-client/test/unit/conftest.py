from hopeit.apps_client import AppsClientSettings
import pytest

from hopeit.app.config import AppConfig, AppConnection, AppDescriptor, AppEngineConfig, \
    EventConnection, EventConnectionType, EventDescriptor, EventType
from hopeit.dataobjects.payload import Payload
from hopeit.server.config import LoggingConfig, ServerConfig
from hopeit.server.version import APPS_API_VERSION


@pytest.fixture
def mock_client_app_config():
    return AppConfig(
        app=AppDescriptor(
            name='mock_client_app',
            version='test'
        ),
        engine=AppEngineConfig(
            import_modules=['mock_client_app']
        ),
        app_connections={
            "test_app_connection": AppConnection(
                name="test_app",
                version=APPS_API_VERSION,
                client="hopeit.apps_client.AppsClient"
            )
        },
        settings={
            "test_app_connection": Payload.to_obj(AppsClientSettings(
                connection_str="http://test-host1,http://test-host2"
            ))
        },
        events={
            "mock_client_event": EventDescriptor(
                type=EventType.GET,
                connections=[
                    EventConnection(
                        app_connection="test_app_connection",
                        event="test_event_get",
                        type=EventConnectionType.GET
                    ),
                    EventConnection(
                        app_connection="test_app_connection",
                        event="test_event_post",
                        type=EventConnectionType.POST
                    )
                ]
            )
        },
        server=ServerConfig(
            logging=LoggingConfig(
                log_level="DEBUG", log_path="work/logs/test/")
        )
    )


@pytest.fixture
def mock_auth(mocker):
    auth_mock = mocker.MagicMock()
    auth_mock.new_token = mocker.MagicMock()
    auth_mock.new_token.return_value = "test_token"
    return auth_mock
