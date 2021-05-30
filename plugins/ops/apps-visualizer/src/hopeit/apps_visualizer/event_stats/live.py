from typing import List, Optional

from hopeit.apps_visualizer.site.visualization import VisualizationOptions
from hopeit.app.api import event_api
from hopeit.app.events import collector_step, Collector
from hopeit.app.context import EventContext

from hopeit.apps_visualizer.event_stats.collect import get_stats
from hopeit.apps_visualizer.site.visualization import visualization_options
from hopeit.apps_visualizer.apps.events_graph import EventsGraphResult, \
    config_graph, cytoscape_data, runtime_apps

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
    query_args=[
        ("app_prefix", Optional[str], "app_key prefix to filter"),
        ("expand_queues", Optional[bool], "if `true` shows each stream queue as a separated stream")
    ],
    responses={
        200: (EventsGraphResult, "Graph Data with applied Live Stats")
    }
)


async def live_stats(collector: Collector, context: EventContext) -> Collector:
    event_stats = get_stats(time_window_secs=30, recent_secs=5)
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
                item['classes'] = f"{item.get('classes', '')} {' '.join(classes)}"
                target = item['data'].get('target', ' ')
                if target[0] == '>':
                    target_item = graph.data[target]
                    target_item['classes'] = f"{target_item['classes']} {' '.join(classes)}"
                if len(source) > 5 and (source[-5:] == ".POST" or source[-4:] == ".GET"):
                    source_item = graph.data[source]
                    source_item['classes'] = f"{source_item['classes']} {' '.join(classes)}"
    return graph


async def build_visualization(collector: Collector, context: EventContext) -> EventsGraphResult:
    return EventsGraphResult(
        runtime_apps=await collector['runtime_apps'],
        graph=await collector['live_stats'],
        options=await collector['payload']
    )