"""
Config Manager: Runtime Apps Config
-----------------------------------------------
Returns runtime configuration of running server
"""
from typing import Optional
import socket
import os

from hopeit.server.runtime import server

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerInfo, ServerStatus
from hopeit.app.api import event_api

logger, extra = app_extra_logger()

__steps__ = ['get_apps_config']

__api__ = event_api(
    summary="Config Manager: Runtime Apps Config",
    description="Returns the runtime config for the Apps running on this server",
    query_args=[("url", Optional[str], "URL used to reach this server, informative")],
    responses={
        200: (RuntimeApps, "Config info about running apps in current process"),
    }
)


async def get_apps_config(payload: None, context: EventContext, *, url: str = "in-process") -> RuntimeApps:
    return RuntimeApps(
        apps={
            app_key: RuntimeAppInfo(
                servers=[ServerInfo(
                    host_name=socket.gethostname(),
                    pid=str(os.getpid()),
                    url=url
                )],
                app_config=app_engine.app_config
            )
            for app_key, app_engine in server.app_engines.items()
        },
        server_status={
            url: ServerStatus.ALIVE
        }
    )
