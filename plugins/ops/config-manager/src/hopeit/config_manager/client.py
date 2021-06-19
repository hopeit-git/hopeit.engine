"""
Config Manager Client
"""
from typing import Dict
import asyncio
import random

import aiohttp

from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit.config_manager import RuntimeApps, RuntimeAppInfo

logger, extra = app_extra_logger()


async def get_apps_config(hosts: str, context: EventContext) -> RuntimeApps:
    """
    Gathers RuntimeApps (runtime apps config) from a given list of hosts running
    `hopeit.config-manager` plugins and returns a combined RuntimeApps
    specifiying for each app_key its configuration and description of hosts where
    it is avalable.

    :param: hosts, str: comma-separated list of the form `http://host:port` where to reach
        servers running hopeit.engine with enabled `config-manager` plugin.
    :return: RuntimeApps, combined from all requested hosts
    """
    runtime_configs = await asyncio.gather(
        *[
            _get_host_config(host, context)
            for host in hosts.split(',')
        ]
    )

    logger.info("Gather hosts config done.")
    apps: Dict[str, RuntimeAppInfo] = {}
    for runtime_apps in runtime_configs:
        _combine_apps(apps, runtime_apps)

    return RuntimeApps(apps=apps)


async def _get_host_config(host: str, context: EventContext) -> RuntimeApps:
    """
    Invokes config-manager runtime-apps-config endpoint in a given host
    """
    # Random <1 sec pause to prevent network overload
    await asyncio.sleep(random.random())

    url = f"{host}/api/config-manager/{APPS_ROUTE_VERSION}/runtime-apps-config?url={host}"
    logger.info(context, "Invoking config-manager on host: {host}...", extra=extra(
        host=host, url=url
    ))
    async with aiohttp.ClientSession() as client:
        async with client.get(url) as response:
            return RuntimeApps.from_dict(await response.json())  # type: ignore


def _combine_apps(apps: Dict[str, RuntimeAppInfo], runtime_apps: RuntimeApps):
    for app_key, app_info in runtime_apps.apps.items():
        app = apps.get(app_key)
        if app is None:
            apps[app_key] = app_info
        else:
            apps[app_key].servers.extend(app_info.servers)
