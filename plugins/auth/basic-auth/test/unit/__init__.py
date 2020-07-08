import pytest  # type: ignore

from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, \
    EventType, parse_app_config_json, AppEngineConfig
from hopeit.server.config import ServerConfig, AuthConfig


@pytest.fixture
def mock_app_config():
    return AppConfig(
        app=AppDescriptor(name='test_app', version='test'),
        engine=AppEngineConfig(),
        env={},
        events={
            'test': EventDescriptor(
                type=EventType.GET
            )
        },
        server=ServerConfig(
            auth=AuthConfig(
                secrets_location='/tmp',
                auth_passphrase='test',
                create_keys=True
            )
        )
    )


@pytest.fixture
def plugin_config():
    with open('plugins/auth/basic-auth/config/1x0.json', 'r') as f:
        return parse_app_config_json(f.read())
