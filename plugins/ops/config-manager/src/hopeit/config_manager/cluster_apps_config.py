from typing import Dict
import socket
import os
import aiohttp

from hopeit.server.runtime import server
from hopeit.server.version import APPS_API_VERSION

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects.jsonify import Json
from hopeit.app.api import event_api

from hopeit.config_manager import RuntimeApps, RuntimeAppInfo

API_VERSION = APPS_API_VERSION.replace('.', 'x')

logger, extra = app_extra_logger()

__steps__ = ['get_apps_config']


__api__ = event_api(
    summary="Config Manager: Cluster Apps Config",
    query_args=[("hosts", str, "Comma-separated list of http://host:port strings")],
    responses={
        200: (RuntimeApps, "Combined config info about running apps in provided list of hosts")
    }
)


async def get_apps_config(payload: None, context: EventContext, hosts: str) -> RuntimeApps:
    apps: Dict[str, RuntimeAppInfo] = {}
    for url in hosts.split(','):
        runtime_apps = await _get_host_config(url)
        _combine_apps(apps, runtime_apps)
    return RuntimeApps(apps=apps)


async def _get_host_config(host: str):
    async with aiohttp.ClientSession() as client:
        async with client.get(
            f"{host}/api/config-manager/{API_VERSION}/runtime-apps-config?url={host}"
        ) as response:
            return RuntimeApps.from_dict(await response.json())


def _combine_apps(apps: Dict[str, RuntimeAppInfo], runtime_apps: RuntimeApps):
    for app_key, app_info in runtime_apps.apps.items():
        app = apps.get(app_key)
        if app is None:
            apps[app_key] = app_info
        else:
            apps[app_key].servers.extend(app_info.servers)
