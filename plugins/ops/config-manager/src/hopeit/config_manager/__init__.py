"""
Config Manager dataobjects
"""
from typing import Dict, List
from enum import Enum

from hopeit.dataobjects import dataobject, Field
from hopeit.app.config import AppConfig, EventDescriptor


@dataobject
class ServerInfo:
    """
    Server info associated with runtime apps
    """
    host_name: str
    pid: str
    url: str = "in-process"


class ServerStatus(str, Enum):
    ALIVE = "ALIVE"
    ERROR = "ERROR"


@dataobject
class RuntimeAppInfo:
    """
    Application config information associated to servers at runtime
    """
    servers: List[ServerInfo]
    app_config: AppConfig
    effective_events: Dict[str, EventDescriptor]


@dataobject
class RuntimeApps:
    """
    Combined App Config and Server Status information for running apps
    """
    apps: Dict[str, RuntimeAppInfo]
    server_status: Dict[str, ServerStatus] = Field(default_factory=dict)
