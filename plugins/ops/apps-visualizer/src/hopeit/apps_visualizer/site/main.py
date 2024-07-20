"""
Events graph showing events, stream and dependencies for specified apps
"""

import os
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.server.names import route_name
from hopeit.app.api import event_api
from hopeit.dataobjects import dataclass, dataobject

from hopeit.config_manager import RuntimeApps

from hopeit.apps_visualizer.apps import get_runtime_apps
from hopeit.apps_visualizer.site.visualization import (
    VisualizationOptions,
    visualization_options_api_args,
    visualization_options,  # noqa: F401
)


__steps__ = ["visualization_options", "runtime_apps_config"]

__api__ = event_api(
    summary="App Visualizer: Site",
    description="[Click here to open Events Graph](/ops/apps-visualizer)",
    query_args=visualization_options_api_args(),
    responses={200: (str, "HTML page with Events Graph")},
)

_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))


@dataobject
@dataclass
class RuntimeAppsConfig:
    runtime_apps: RuntimeApps
    options: VisualizationOptions


async def runtime_apps_config(
    options: VisualizationOptions, context: EventContext
) -> RuntimeAppsConfig:
    """
    Extract current runtime app_config objects
    """
    return RuntimeAppsConfig(
        runtime_apps=await get_runtime_apps(
            context, refresh=True, expand_events=options.expanded_view
        ),
        options=options,
    )


async def __postprocess__(
    result: RuntimeAppsConfig, context: EventContext, response: PostprocessHook
) -> str:
    """
    Renders html from template, using cytospace data json
    """
    response.set_content_type("text/html")

    app_prefix = result.options.app_prefix

    view_link = f"apps-visualizer?app_prefix={result.options.app_prefix}"
    view_link += f"&host_filter={result.options.host_filter}"
    view_link += f"&expanded_view={str(not result.options.expanded_view).lower()}"
    view_link += f"&live={str(result.options.live).lower()}"

    live_link = f"apps-visualizer?app_prefix={result.options.app_prefix}"
    live_link += f"&host_filter={result.options.host_filter}"
    live_link += f"&expanded_view={str(result.options.expanded_view).lower()}"
    live_link += f"&live={str(not result.options.live).lower()}"

    app_prefix = (
        f"{result.options.app_prefix}*" if result.options.app_prefix else "All running apps"
    )
    host_filter = f"*{result.options.host_filter}*" if result.options.host_filter else "All servers"
    view_type = "Effective Events" if result.options.expanded_view else "Configured Events"
    live_type = "Live!" if result.options.live else "Static"

    refresh_endpoint_comps = (
        ["event-stats", "live"] if result.options.live else ["apps", "events-graph"]
    )
    refresh_endpoint = route_name(
        "api", context.app.name, context.app.version, *refresh_endpoint_comps
    )
    refresh_endpoint += f"?app_prefix={result.options.app_prefix}"
    refresh_endpoint += f"&host_filter={result.options.host_filter}"
    refresh_endpoint += f"&expanded_view={str(result.options.expanded_view).lower()}"
    refresh_endpoint += f"&live={str(result.options.live).lower()}"

    with open(_dir_path / "events_graph_template.html") as f:
        template = f.read()
        template = template.replace("{{ app_prefix }}", app_prefix)
        template = template.replace("{{ host_filter }}", host_filter)
        template = template.replace("{{ view_link }}", view_link)
        template = template.replace("{{ live_link }}", live_link)
        template = template.replace("{{ refresh_endpoint }}", refresh_endpoint)
        template = template.replace("{{ view_type }}", view_type)
        template = template.replace("{{ live_type }}", live_type)
        return template
