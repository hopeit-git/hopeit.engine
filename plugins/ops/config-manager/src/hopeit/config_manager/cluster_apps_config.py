"""
Cluster Apps Config
----------------------------------------------------------------------------------------
Handle remote access to runtime configuration from a group of hosts running hopeit.engine
"""
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.app.api import event_api

from hopeit.config_manager import RuntimeApps, client

logger, extra = app_extra_logger()

__steps__ = ['get_hosts_apps_config']

__api__ = event_api(
    summary="Config Manager: Cluster Apps Config",
    description="Handle remote access to runtime configuration for a group of hosts",
    query_args=[("hosts", str, "Comma-separated list of http://host:port strings")],
    responses={
        200: (RuntimeApps, "Combined config info about running apps in provided list of hosts")
    }
)


async def get_hosts_apps_config(payload: None, context: EventContext, *, hosts: str) -> RuntimeApps:
    return await client.get_apps_config(hosts, context)
