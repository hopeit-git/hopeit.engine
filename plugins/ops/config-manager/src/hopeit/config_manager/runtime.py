"""
Manage access to server runtime running applications
"""
import socket
import os
from typing import Dict
from hopeit.app.config import AppConfig, EventDescriptor, EventPlugMode

from hopeit.server import runtime

from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerInfo, ServerStatus
from hopeit.server.engine import AppEngine

from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages


def _effective_events(app_engine: AppEngine, expand_events: bool) -> Dict[str, EventDescriptor]:
    active_events = {}
    app_config = app_engine.app_config
    app_key = app_config.app_key()
    for plugin_info in app_config.plugins:
        plugin_engine = runtime.server.app_engines[plugin_info.app_key()]
        plugin_config = plugin_engine.app_config
        plugin_key = plugin_config.app_key()
        events = plugin_engine.effective_events if expand_events else plugin_config.events
        for event_name, event_info in events.items():
            if event_info.plug_mode == EventPlugMode.ON_APP:
                active_events[f"{app_key}.{plugin_key}.{event_name}"] = event_info

    events = app_engine.effective_events if expand_events else app_config.events
    for event_name, event_info in events.items():
        if event_info.plug_mode != EventPlugMode.ON_APP:
            active_events[f"{app_key}.{event_name}"] = event_info

    return active_events


def get_in_process_config(url: str, expand_events: bool):
    return RuntimeApps(
        apps={
            app_key: RuntimeAppInfo(
                servers=[ServerInfo(
                    host_name=socket.gethostname(),
                    pid=str(os.getpid()),
                    url=url
                )],
                app_config=app_engine.app_config,
                effective_events=_effective_events(app_engine, expand_events=expand_events)
            )
            for app_key, app_engine in runtime.server.app_engines.items()
        },
        server_status={
            url: ServerStatus.ALIVE
        }
    )
