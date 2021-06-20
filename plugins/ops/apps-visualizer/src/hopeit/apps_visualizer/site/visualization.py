"""
Visualization metadata
"""
from hopeit.app.context import EventContext
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from hopeit.dataobjects import dataobject


@dataobject
@dataclass
class CytoscapeGraph:
    data: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataobject
@dataclass
class VisualizationOptions:
    app_prefix: str = ''
    host_filter: str = ''
    expand_queues: bool = False
    live: bool = False


def visualization_options_api_args():
    return [
        ("app_prefix", Optional[str], "app name prefix to filter"),
        ("host_filter", Optional[str], "host name filter substring"),
        ("expand_queues", Optional[bool], "if `true` shows each stream queue as a separated stream"),
        ("live", Optional[bool], "if `true` enable live stats refreshing")
    ]


async def visualization_options(payload: None, context: EventContext,
                                *, app_prefix: str = '',
                                host_filter: str = '',
                                expand_queues: bool = False,
                                live: bool = False) -> VisualizationOptions:
    return VisualizationOptions(
        app_prefix=app_prefix,
        host_filter=host_filter,
        expand_queues=expand_queues is True or expand_queues == 'true',
        live=live is True or live == 'true'
    )
