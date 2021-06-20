"""
Config Manager dataclasses
"""
from typing import Dict, List
from enum import Enum
from dataclasses import dataclass, field

from hopeit.dataobjects import dataobject
from hopeit.app.config import AppConfig


@dataobject
@dataclass
class ServerInfo:
    """
    Server info associated with runtime apps
    """
    host_name: str
    pid: str
    url: str = "in-process"


class ServerStatus(Enum):
    ALIVE = "ALIVE"
    ERROR = "ERROR"


@dataobject
@dataclass
class RuntimeAppInfo:
    """
    Application config information associated to servers at runtime
    """
    servers: List[ServerInfo]
    app_config: AppConfig


@dataobject
@dataclass
class RuntimeApps:
    """
    Combined App Config and Server Status information for running apps
    """
    apps: Dict[str, RuntimeAppInfo]
    server_status: Dict[str, ServerStatus] = field(default_factory=dict)
