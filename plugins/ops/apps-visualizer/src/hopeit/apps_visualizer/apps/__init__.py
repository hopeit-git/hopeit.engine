"""
Apps Visualizer apps state
"""
from typing import Optional
import asyncio
from datetime import datetime, timezone

from hopeit.app.context import EventContext
from hopeit.server.logger import engine_extra_logger

from hopeit.config_manager import RuntimeApps
from hopeit.config_manager.client import get_apps_config

from hopeit.apps_visualizer import AppsVisualizerEnv

logger, extra = engine_extra_logger()

_lock = asyncio.Lock()
_apps: Optional[RuntimeApps] = None
_expire: float = 0.0


async def get_runtime_apps(context: EventContext, refresh: bool = False) -> RuntimeApps:
    """
    Extract current runtime app_config objects
    """
    global _apps, _expire
    if not refresh and _lock.locked():
        raise RuntimeError("Events graph request in process. Ignoring")
    env = AppsVisualizerEnv.from_context(context)
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    async with _lock:
        if _apps is None or refresh or now_ts > _expire:
            logger.info(context, "Contacting hosts config-manager...")
            _apps = await get_apps_config(env.hosts, context)
            _expire = now_ts + env.refresh_hosts_seconds
        else:
            logger.info(context, "Using cached runtime apps information.")
        return _apps
