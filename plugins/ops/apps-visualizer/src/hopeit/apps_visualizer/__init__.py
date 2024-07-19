"""
Apps Visualizer plugin module
"""

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class AppsVisualizerSettings:
    """
    Apps visualizer settings.

    Helper dataclasses to load "apps-visualizer" env section from plugin config.

    :field: hosts, str: comma-separated list of `http://host:port` entries to contact to query
        config-manager plugin for running apps layout
    :field: refresh_hosts_seconds: int, default 60: interval to contact nodes config-manager
    :field: live_recent_treshold_seconds, int, default 10: number of seconds to consider a node
        recently activated (the complete box will be highlighted)
    :field: live_active_treshold_seconds, int, default: 60: number of seconds to consider a node
        has been activated (border will be highlighted)
    """

    hosts: str
    refresh_hosts_seconds: int = 60
    live_recent_treshold_seconds: int = 10
    live_active_treshold_seconds: int = 60
