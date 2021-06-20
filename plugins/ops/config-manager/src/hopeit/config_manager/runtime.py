"""
Manage access to server runtime running applications
"""
import socket
import os

from hopeit.server import runtime

from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerInfo, ServerStatus


def get_in_process_config(url: str):
    return RuntimeApps(
        apps={
            app_key: RuntimeAppInfo(
                servers=[ServerInfo(
                    host_name=socket.gethostname(),
                    pid=str(os.getpid()),
                    url=url
                )],
                app_config=app_engine.app_config
            )
            for app_key, app_engine in runtime.server.app_engines.items()
        },
        server_status={
            url: ServerStatus.ALIVE
        }
    )
