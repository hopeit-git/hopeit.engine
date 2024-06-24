"""
Config Manager Client
"""
from typing import Dict, Union, Tuple
import asyncio
import random

import aiohttp

from hopeit.dataobjects.payload import Payload
from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from hopeit.server.logger import engine_extra_logger

from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerStatus
from hopeit.config_manager.runtime import get_in_process_config

logger, extra = engine_extra_logger()


@dataobject
@dataclass
class ConfigManagerClientSettings:
    """
    File storage plugin config


    :field: client_timeout, float: client timeout in seconds, defults to 10.0
    """
    client_timeout: float = 10.0


async def get_apps_config(hosts: str, context: EventContext, **kwargs) -> RuntimeApps:
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
        *[_get_host_config(host, context, **kwargs) for host in hosts.split(",")]
    )

    apps: Dict[str, RuntimeAppInfo] = {}
    server_status: Dict[str, ServerStatus] = {}
    for host, runtime_apps_response in responses:
        if isinstance(runtime_apps_response, RuntimeApps):
            _combine_apps(apps, runtime_apps_response)
            server_status[host] = runtime_apps_response.server_status.get(
                host, ServerStatus.ALIVE
            )
        elif isinstance(runtime_apps_response, ServerStatus):
            server_status[host] = runtime_apps_response

    return RuntimeApps(apps=apps, server_status=server_status)


async def _get_host_config(
    host: str, context: EventContext, **kwargs
) -> Tuple[str, Union[RuntimeApps, ServerStatus]]:
    """
    Invokes config-manager runtime-apps-config endpoint in a given host
    """

    settings: ConfigManagerClientSettings = context.settings(
        key="config_manager_client", datatype=ConfigManagerClientSettings
    )

    if host == "in-process":
        return host, get_in_process_config(host, **kwargs)

    # Random <1 sec pause to prevent network overload
    await asyncio.sleep(random.random())

    url = (
        f"{host}/api/config-manager/{APPS_ROUTE_VERSION}/runtime-apps-config?url={host}"
    )
    for k, v in kwargs.items():
        url += f"&{k}={v}".lower()

    logger.info(
        context,
        "Invoking config-manager on host: %s...",
        host,
        extra=extra(host=host, url=url),
    )

    try:
        timeout = aiohttp.ClientTimeout(total=settings.client_timeout)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.get(url) as response:
                return host, Payload.from_obj(await response.json(), RuntimeApps)
    except TimeoutError as e:  # pylint: disable=broad-except
        logger.error(
            context,
            "Timeout contacting host: %s",
            host,
            extra=extra(host=host, url=url, error=str(e)),
        )
        return host, ServerStatus.ERROR
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            context,
            "Error contacting host: %s",
            host,
            extra=extra(host=host, url=url, error=str(e)),
        )
        return host, ServerStatus.ERROR


def _combine_apps(apps: Dict[str, RuntimeAppInfo], runtime_apps: RuntimeApps):
    for app_key, app_info in runtime_apps.apps.items():
        app = apps.get(app_key)
        if app is None:
            apps[app_key] = app_info
        else:
            apps[app_key].servers.extend(app_info.servers)
