from typing import List

from hopeit.apps_visualizer.site.visualization import VisualizationOptions
from hopeit.app.api import event_api
from hopeit.app.events import collector_step, Collector
from hopeit.app.context import EventContext

from hopeit.apps_visualizer.event_stats.collect import get_stats
from hopeit.apps_visualizer.site.visualization import \
    visualization_options, visualization_options_api_args  # noqa: F401
from hopeit.apps_visualizer.apps.events_graph import EventsGraphResult, \
    config_graph, cytoscape_data, runtime_apps  # noqa: F401
from hopeit.apps_visualizer import AppsVisualizerEnv

__steps__ = [
    'visualization_options',
    collector_step(payload=VisualizationOptions).gather(
        'runtime_apps',
        'config_graph',
        'cytoscape_data',
        'live_stats'
    ),
    'build_visualization'
]

__api__ = event_api(
    summary="App Visualizer: Live Stats",
    description="App Visualizer: Live Stats",
    query_args=visualization_options_api_args(),
    responses={
        200: (EventsGraphResult, "Graph Data with applied Live Stats")
    }
)


def _classes(item: dict, new_classes: List[str]) -> str:
    return ' '.join(sorted(
        {*item.get('classes', '').split(' '), *new_classes}
    )).lstrip(' ')


async def live_stats(collector: Collector, context: EventContext) -> Collector:
    env = AppsVisualizerEnv.from_context(context)
    apps = await collector['runtime_apps']
    options = await collector['payload']
    host_pids = set(
        (server.host_name, server.pid)
        for _, runtime_info in apps.apps.items()
        for server in runtime_info.servers
        if options.host_filter in server.url
    )
    event_stats = get_stats(
        host_pids=host_pids,
        time_window_secs=env.live_active_treshold_seconds,
        recent_secs=env.live_recent_treshold_seconds
    )
    graph = await collector['cytoscape_data']
    if len(event_stats) == 0:
        return graph

    for item_id, item in graph.data.items():
        label = item['data'].get('label', '')
        source = item['data'].get('source', '')
        target = item['data'].get('target', '')
        if label and source and source[0] == '>' and source[-len(label):] != label:
            source += '.' + label
        if target and target[0] == '>':
            target = ''
        keys = filter(bool, [item_id, source, target])

        classes = []
        for key in keys:
            s = event_stats.get(key)
            if s:
                if s.started:
                    classes.append('STARTED')
                if s.pending:
                    classes.append('PENDING')
                if s.recent:
                    classes.append('RECENT')
                if s.failed:
                    classes.append('FAILED')
                item['classes'] = _classes(item, classes)
                target = item['data'].get('target', ' ')
                if target[0] == '>':
                    target_item = graph.data[target]
                    target_item['classes'] = _classes(target_item, classes)
                if len(source) > 5 and (
                    source[-5:] == ".POST" or source[-4:] == ".GET" or source[-8:] == "MULTIPART"
                ):
                    source_item = graph.data[source]
                    source_item['classes'] = _classes(source_item, classes)
    return graph


async def build_visualization(collector: Collector, context: EventContext) -> EventsGraphResult:
    return EventsGraphResult(
        runtime_apps=await collector['runtime_apps'],
        graph=await collector['live_stats'],
        options=await collector['payload']
    )
