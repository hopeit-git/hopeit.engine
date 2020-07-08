import pytest  # type: ignore

from hopeit.app.config import AppConfig, AppDescriptor, \
    EventDescriptor, EventType, EventPlugMode
from hopeit.server.config import ServerConfig, LoggingConfig


@pytest.fixture
def mock_plugin_config():
    return AppConfig(
        app=AppDescriptor(name='mock_plugin', version='test'),
        env={
            'plugin': {
                'plugin_value': 'test_plugin_value',
                'custom_value': 'test_custom_value'
            }
        },
        events={
            'plugin_event': EventDescriptor(
                type=EventType.GET,
                plug_mode=EventPlugMode.ON_APP
            )
        },
        server=ServerConfig(
            logging=LoggingConfig(log_level="DEBUG", log_path="work/logs/test/")
        )
    )
