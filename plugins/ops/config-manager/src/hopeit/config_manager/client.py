"""
Config Manager Client
"""
from typing import Dict, Union, Tuple, Optional
import asyncio
import random

import aiohttp

from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.app.context import EventContext
from hopeit.server.logger import engine_extra_logger

from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerStatus
from hopeit.config_manager.runtime import get_in_process_config

logger, extra = engine_extra_logger()


async def get_apps_config(hosts: str, context: Optional[EventContext] = None) -> RuntimeApps:
    """
    Gathers RuntimeApps (runtime apps config) from a given list of hosts running
    `hopeit.config-manager` plugins and returns a combined RuntimeApps
    specifiying for each app_key its configuration and description of hosts where
    it is avalable.

    :param: hosts, str: comma-separated list of the form `http://host:port` where to reach
        servers running hopeit.engine with enabled `config-manager` plugin.
    :return: RuntimeApps, combined from all requested hosts
    """
    responses = await asyncio.gather(
        *[
            _get_host_config(host, context)
            for host in hosts.split(',')
        ]
    )

    apps: Dict[str, RuntimeAppInfo] = {}
    server_status: Dict[str, ServerStatus] = {}
    for host, runtime_apps_response in responses:
        if isinstance(runtime_apps_response, RuntimeApps):
            _combine_apps(apps, runtime_apps_response)
            server_status[host] = runtime_apps_response.server_status.get(host, ServerStatus.ALIVE)
        elif isinstance(runtime_apps_response, ServerStatus):
            server_status[host] = runtime_apps_response

    return RuntimeApps(apps=apps, server_status=server_status)


async def _get_host_config(host: str,
                           context: Optional[EventContext] = None
                           ) -> Tuple[str, Union[RuntimeApps, ServerStatus]]:
    """
    Invokes config-manager runtime-apps-config endpoint in a given host
    """
    if host == "in-process":
        return host, get_in_process_config(host)

    # Random <1 sec pause to prevent network overload
    await asyncio.sleep(random.random())

    url = f"{host}/api/config-manager/{APPS_ROUTE_VERSION}/runtime-apps-config?url={host}"
    logger.info(context or __name__, "Invoking config-manager on host: %s...", host, extra=extra(
        host=host, url=url
    ))

    try:
        async with aiohttp.ClientSession() as client:
            async with client.get(url) as response:
                return host, RuntimeApps.from_dict(await response.json())  # type: ignore
    except Exception as e:  # pylint: disable=broad-except
        logger.error(context or __name__, "Error contacting host: %s", host, extra=extra(
            host=host, url=url, error=str(e)
        ))
        return host, ServerStatus.ERROR


def _combine_apps(apps: Dict[str, RuntimeAppInfo], runtime_apps: RuntimeApps):
    for app_key, app_info in runtime_apps.apps.items():
        app = apps.get(app_key)
        if app is None:
            apps[app_key] = app_info
        else:
            apps[app_key].servers.extend(app_info.servers)
