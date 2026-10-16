"""
Visualization metadata
"""

from typing import Any, Optional

from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject, field


@dataobject
@dataclass
class CytoscapeGraph:
    data: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataobject
@dataclass
class VisualizationOptions:
    app_prefix: str = ""
    host_filter: str = ""
    expanded_view: bool = False
    live: bool = False


def visualization_options_api_args():
    return [
        ("app_prefix", str | None, "app name prefix to filter"),
        ("host_filter", str | None, "host name filter substring"),
        (
            "expanded_view",
            bool | None,
            "if `true` shows each stream queue as a separated stream",
        ),
        ("live", bool | None, "if `true` enable live stats refreshing"),
    ]


async def visualization_options(
    payload: None,
    context: EventContext,
    *,
    app_prefix: str = "",
    host_filter: str = "",
    expanded_view: bool = False,
    live: bool = False,
) -> VisualizationOptions:
    return VisualizationOptions(
        app_prefix=app_prefix,
        host_filter=host_filter,
        expanded_view=expanded_view is True or expanded_view == "true",
        live=live is True or live == "true",
    )
