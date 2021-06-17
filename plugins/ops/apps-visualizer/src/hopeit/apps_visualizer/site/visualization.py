"""
Visualization metadata
"""
from hopeit.app.context import EventContext
from typing import Dict, Any
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
    expand_queues: bool = False
    live: bool = False


async def visualization_options(payload: None, context: EventContext,
                                *, app_prefix: str = '',
                                expand_queues: bool = False,
                                live: bool = False) -> VisualizationOptions:
    return VisualizationOptions(
        app_prefix=app_prefix,
        expand_queues=expand_queues is True or expand_queues == 'true',
        live=live is True or live == 'true'
    )
