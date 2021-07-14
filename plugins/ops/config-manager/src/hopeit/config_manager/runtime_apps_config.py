"""
Config Manager: Runtime Apps Config
-----------------------------------------------
Returns runtime configuration of running server
"""
from typing import Optional

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit.config_manager import RuntimeApps
from hopeit.app.api import event_api
from hopeit.config_manager.runtime import get_in_process_config

logger, extra = app_extra_logger()

__steps__ = ['get_apps_config']

__api__ = event_api(
    summary="Config Manager: Runtime Apps Config",
    description="Returns the runtime config for the Apps running on this server",
    query_args=[
        ("url", Optional[str], "URL used to reach this server, informative"),
        ("expand_events", Optional[bool], "Retrieve expanded effective events from event steps")
    ],
    responses={
        200: (RuntimeApps, "Config info about running apps in current process"),
    }
)


async def get_apps_config(
    payload: None, context: EventContext,
    *, url: str = "in-process", expand_events: bool = False
) -> RuntimeApps:
    return get_in_process_config(
        url, expand_events=expand_events is True or expand_events == "true"
    )
