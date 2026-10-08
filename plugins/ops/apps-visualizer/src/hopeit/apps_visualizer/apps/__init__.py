"""
Apps Visualizer apps state
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from hopeit.app.context import EventContext
from hopeit.apps_visualizer import AppsVisualizerSettings
from hopeit.config_manager import RuntimeApps
from hopeit.config_manager.client import get_apps_config
from hopeit.server.logger import engine_extra_logger

logger, extra = engine_extra_logger()

_lock = asyncio.Lock()
_apps: Optional[RuntimeApps] = None
_expire: float = 0.0


async def get_runtime_apps(
    context: EventContext, *, refresh: bool = False, expand_events: bool = False
) -> RuntimeApps:
    """
    Extract current runtime app_config objects
    """
    global _apps, _expire
    if not refresh and _lock.locked():
        raise RuntimeError("Events graph request in process. Ignoring")
    settings = context.settings(key="apps_visualizer", datatype=AppsVisualizerSettings)
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    async with _lock:
        if _apps is None or refresh or now_ts > _expire:
            logger.info(context, "Contacting hosts config-manager...")
            _apps = await get_apps_config(settings.hosts, context, expand_events=expand_events)
            _expire = now_ts + settings.refresh_hosts_seconds
        else:
            logger.info(context, "Using cached runtime apps information.")
        return _apps
