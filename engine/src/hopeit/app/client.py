"""
Base class and helper functions to defined and invoke external apps
using clients plugins.
"""
from typing import Optional, Type, Union, List
from abc import ABC
from importlib import import_module

from hopeit.app.context import EventContext
from hopeit.app.config import AppConfig
from hopeit.dataobjects import EventPayload, EventPayloadType
from hopeit.server.logger import engine_logger, extra_logger

logger = engine_logger()
extra = extra_logger()

_registered_clients = {}


class ClientException(Exception):
    """Base exception for Client errors"""


class AppConnectionNotFound(ClientException):
    """Invalid app_connection or not registered"""


class Client(ABC):
    """
    Base class to imeplement stream management of a Hopeit App
    """
    @staticmethod
    def create(app_config: AppConfig, app_connection: str):
        connection_info = app_config.app_connections[app_connection]
        cm_comps = connection_info.client.split('.')
        module_name, impl_name = '.'.join(cm_comps[:-1]), cm_comps[-1]
        logger.info(__name__, f"Importing Client module: {module_name} implementation: {impl_name}...")
        module = import_module(module_name)
        impl = getattr(module, impl_name)
        logger.info(__name__, f"Creating {impl_name} for app_connection {app_connection}...")
        return impl(app_config, app_connection)

    async def start(self):
        raise NotImplementedError()

    async def stop(self):
        raise NotImplementedError()

    async def call(self, event_name: str,
                   *, datatype: Type[EventPayloadType], payload: Optional[EventPayload],
                   context: EventContext, **kwargs) -> Union[EventPayloadType, List[EventPayloadType]]:
        raise NotImplementedError()


async def register_app_connections(app_config: AppConfig):
    _registered_clients[app_config.app_key()] = {
        app_connection: await Client.create(app_config, app_connection).start()
        for app_connection in app_config.app_connections.keys()
    }


async def stop_app_connections(app_key: str):
    for _, client in _registered_clients[app_key].items():
        await client.stop()
    del _registered_clients[app_key]


def app_client(app_connection: str, context: EventContext) -> Client:
    try:
        return _registered_clients[context.app_key][app_connection]
    except KeyError:
        raise AppConnectionNotFound(  # pylint: disable=raise-missing-from
            f"Not found app_connection: {app_connection} for app: {context.app_key}"
        )


async def app_call(app_connection: str,
                   *, event: str, datatype: Type[EventPayloadType],
                   payload: EventPayload, context: EventContext,
                   **kwargs) -> Union[EventPayloadType, List[EventPayloadType]]:
    client = app_client(app_connection, context)
    return await client.call(
        event, datatype=datatype, payload=payload, context=context, **kwargs
    )
