"""
Visualization metadata
"""
from typing import Dict, Any, List
from dataclasses import dataclass, field

from hopeit.dataobjects import dataobject


@dataobject
@dataclass
class CytoscapeGraph:
    data: List[Dict[str, Any]] = field(default_factory=list)


@dataobject
@dataclass
class VisualizationOptions:
    app_prefix: str = ''
    expand_queues: bool = False
