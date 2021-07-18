"""
Manage access to server runtime running applications
"""
import socket
import os
from typing import Dict
from hopeit.app.config import AppConfig, EventDescriptor, EventPlugMode

from hopeit.server import runtime

from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerInfo, ServerStatus

from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages


def _effective_events(app_config: AppConfig, expand_events: bool) -> Dict[str, EventDescriptor]:
    active_events = {}
    for plugin_info in app_config.plugins:
        plugin_config = runtime.server.app_engines[plugin_info.app_key()].app_config
        for event_name, event_info in plugin_config.events.items():
            if event_info.plug_mode == EventPlugMode.ON_APP:
                active_events[event_name] = event_info

    for event_name, event_info in app_config.events.items():
        if event_info.plug_mode != EventPlugMode.ON_APP:
            active_events[event_name] = event_info

    if expand_events:
        expanded_events = {}
        for event_name, event_info in active_events.items():
            impl = find_event_handler(app_config=app_config, event_name=event_name)
            splits = split_event_stages(app_config.app, event_name, event_info, impl)
            for name, info in splits.items():
                expanded_events[name] = info
        return expanded_events

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
                effective_events=_effective_events(app_engine.app_config, expand_events=expand_events)
            )
            for app_key, app_engine in runtime.server.app_engines.items()
        },
        server_status={
            url: ServerStatus.ALIVE
        }
    )
