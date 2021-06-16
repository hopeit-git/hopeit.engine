"""
Events graph showing events, stream and dependecies for specified apps
"""
import os
import sys
from typing import List, Optional
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.site.visualization import VisualizationOptions, \
    visualization_options  # noqa: F401
from hopeit.server.names import route_name
from hopeit.app.api import event_api
from hopeit.dataobjects import dataclass, dataobject
from hopeit.app.config import AppConfig

__steps__ = [
    'visualization_options',
    'runtime_apps'
]

__api__ = event_api(
    summary="App Visualizer: Site",
    description="[Click here to open Events Graph](/ops/apps-visualizer)",
    query_args=[
        ("app_prefix", Optional[str], "app_key prefix to filter"),
        ("expand_queues", Optional[bool], "if `true` shows each stream queue as a separated stream"),
        ("live", Optional[bool], "if `true` enable live stats refreshing")
    ],
    responses={
        200: (str, "HTML page with Events Graph")
    }
)

_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))


@dataobject
@dataclass
class RuntimeApps:
    apps: List[AppConfig]


@dataobject
@dataclass
class EventsGraphResult:
    runtime_apps: RuntimeApps
    options: VisualizationOptions


async def runtime_apps(options: VisualizationOptions, context: EventContext) -> EventsGraphResult:
    """
    Extract current runtime app_config objects
    """
    server = getattr(sys.modules.get("hopeit.server.runtime"), "server")
    apps = RuntimeApps(
        apps=sorted(
            (app.app_config for app in server.app_engines.values()),
            key=lambda x: x.app_key()
        )
    )
    return EventsGraphResult(
        runtime_apps=apps,
        options=options
    )


async def __postprocess__(result: EventsGraphResult, context: EventContext, response: PostprocessHook) -> str:
    """
    Renders html from template, using cytospace data json
    """
    response.set_content_type("text/html")

    app_prefix = result.options.app_prefix
    app_names = [
        ("All runtime apps", ""),
        *((app_config.app.name, app_config.app.name) for app_config in result.runtime_apps.apps)
    ]
    app_items = '\n'.join(
        [
            f'<li><a class="dropdown-item'
            f'{" active" if app_prefix and name[0:len(app_prefix)] == app_prefix else ""}"'
            f' href="apps-visualizer?app_prefix={prefix}'
            f"&expand_queues={str(result.options.expand_queues).lower()}"
            f"&live={str(result.options.live).lower()}"
            f'">{name}</a></li>'
            for name, prefix in app_names
        ]
    )

    switch_link = f"apps-visualizer?app_prefix={result.options.app_prefix}"
    switch_link += f"&expand_queues={str(not result.options.expand_queues).lower()}"
    switch_link += f"&live={str(result.options.live).lower()}"

    live_link = f"apps-visualizer?app_prefix={result.options.app_prefix}"
    live_link += f"&expand_queues={str(result.options.expand_queues).lower()}"
    live_link += f"&live={str(not result.options.live).lower()}"

    app_prefix = result.options.app_prefix or 'All running apps'
    view_type = "Expanded queues view" if result.options.expand_queues else "Standard view"
    live_type = "Live!" if result.options.live else "Static"

    refresh_endpoint_comps = (
        ['event-stats', 'live'] if result.options.live else ['apps', 'events-graph']
    )
    refresh_endpoint = route_name("api", context.app.name, context.app.version, *refresh_endpoint_comps)
    refresh_endpoint += f"?app_prefix={result.options.app_prefix}"
    refresh_endpoint += f"&expand_queues={str(result.options.expand_queues).lower()}"

    with open(_dir_path / 'events_graph_template.html') as f:
        template = f.read()
        template = template.replace("{{ app_items }}", app_items)
        template = template.replace("{{ app_prefix }}", app_prefix)
        template = template.replace("{{ switch_link }}", switch_link)
        template = template.replace("{{ live_link }}", live_link)
        template = template.replace("{{ refresh_endpoint }}", refresh_endpoint)
        template = template.replace("{{ view_type }}", view_type)
        template = template.replace("{{ live_type }}", live_type)
        return template
