from typing import Any, Dict, List, Optional, Tuple, Type

from abc import ABC
from importlib import import_module

from hopeit.app.context import EventContext
from hopeit.app.config import AppConfig, AppConnection
from hopeit.dataobjects import EventPayload
from hopeit.server.logger import engine_logger, extra_logger

logger = engine_logger()
extra = extra_logger()

_registered_clients = {}


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

    async def call(self, app_connection: str, event_name: str,
                   *, datatype: Type[EventPayload], payload: Optional[EventPayload],
                   context: EventContext, **kwargs) -> EventPayload:
        raise NotImplementedError()


async def register_apps_client(app_config: AppConfig):
    _registered_clients[app_config.app_key()] = {
        app_connection: await Client.create(app_config, app_connection).start()
        for app_connection in app_config.app_connections.keys()
    }


def app_client(app_connection: str, context: EventContext) -> Client:
    return _registered_clients[context.app_key][app_connection]
