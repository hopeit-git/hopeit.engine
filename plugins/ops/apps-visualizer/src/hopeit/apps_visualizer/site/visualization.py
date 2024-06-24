"""
Visualization metadata
"""
from hopeit.app.context import EventContext
from typing import Dict, Any, Optional

from hopeit.dataobjects import dataclass, dataobject, field


@dataobject
@dataclass
class CytoscapeGraph:
    data: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataobject
@dataclass
class VisualizationOptions:
    app_prefix: str = ''
    host_filter: str = ''
    expanded_view: bool = False
    live: bool = False


def visualization_options_api_args():
    return [
        ("app_prefix", Optional[str], "app name prefix to filter"),
        ("host_filter", Optional[str], "host name filter substring"),
        ("expanded_view", Optional[bool], "if `true` shows each stream queue as a separated stream"),
        ("live", Optional[bool], "if `true` enable live stats refreshing")
    ]


async def visualization_options(payload: None, context: EventContext,
                                *, app_prefix: str = '',
                                host_filter: str = '',
                                expanded_view: bool = False,
                                live: bool = False) -> VisualizationOptions:
    return VisualizationOptions(
        app_prefix=app_prefix,
        host_filter=host_filter,
        expanded_view=expanded_view is True or expanded_view == 'true',
        live=live is True or live == 'true'
    )
