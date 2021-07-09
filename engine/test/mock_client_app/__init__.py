from typing import List, Optional, Type, Union
import pytest

from hopeit.app.config import AppConfig, AppConnection, AppDescriptor, AppEngineConfig, \
    EventConnection, EventConnectionType, EventDescriptor, EventType
from hopeit.dataobjects import EventPayload
from hopeit.server.config import LoggingConfig, ServerConfig
from hopeit.server.version import APPS_API_VERSION
from hopeit.app.context import EventContext
from hopeit.app.events import EventPayloadType
from hopeit.app.client import Client


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
                client="mock_client_app.MockClient"
            )
        },
        events={
            "mock_client_event": EventDescriptor(
                type=EventType.GET,
                connections=[
                    EventConnection(
                        app_connection="test_app_connection",
                        event="test_event",
                        type=EventConnectionType.GET
                    )
                ]
            )
        },
        server=ServerConfig(
            logging=LoggingConfig(
                log_level="DEBUG", log_path="work/logs/test/")
        )
    )


class MockClient(Client):

    def __init__(self, app_config: AppConfig, app_connection: str):
        self.app_config = app_config
        self.app_connection = app_connection
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True
        return self

    async def stop(self):
        self.stopped = True

    async def call(self, event_name: str,
                   *, datatype: Type[EventPayloadType], payload: Optional[EventPayload],
                   context: EventContext, **kwargs) -> Union[EventPayloadType, List[EventPayloadType]]:
        return {  # type: ignore
            "app_connection": self.app_connection,
            "event": event_name,
            "payload": payload
        }
