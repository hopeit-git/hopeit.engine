"""
Config Manager dataclasses
"""
from typing import Dict, List

from hopeit.dataobjects import dataclass, dataobject
from hopeit.app.config import AppConfig


@dataobject
@dataclass
class ServerInfo:
    host_name: str
    pid: str
    url: str = "in-process"


@dataobject
@dataclass
class RuntimeAppInfo:
    servers: List[ServerInfo]
    app_config: AppConfig


@dataobject
@dataclass
class RuntimeApps:
    apps: Dict[str, RuntimeAppInfo]
