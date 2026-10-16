"""
Config Manager dataclasses
"""

from enum import Enum
from typing import Dict, List

from hopeit.app.config import AppConfig, EventDescriptor
from hopeit.dataobjects import dataclass, dataobject, field


@dataobject
@dataclass
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
@dataclass
class RuntimeAppInfo:
    """
    Application config information associated to servers at runtime
    """

    servers: list[ServerInfo]
    app_config: AppConfig
    effective_events: dict[str, EventDescriptor]


@dataobject
@dataclass
class RuntimeApps:
    """
    Combined App Config and Server Status information for running apps
    """

    apps: dict[str, RuntimeAppInfo]
    server_status: dict[str, ServerStatus] = field(default_factory=dict)
