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
    host_name: str
    pid: str
    url: str = "in-process"


class ServerStatus(Enum):
    ALIVE = "ALIVE"
    ERROR = "ERROR"


@dataobject
@dataclass
class RuntimeAppInfo:
    servers: List[ServerInfo]
    app_config: AppConfig


@dataobject
@dataclass
class RuntimeApps:
    apps: Dict[str, RuntimeAppInfo]
    server_status: Dict[str, ServerStatus] = field(default_factory=dict)
