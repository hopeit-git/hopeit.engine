"""
Events graph showing events, stream and dependecies for specified apps
"""
import os
import sys
from typing import Optional
import json
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.graphs import Edge, Node, Graph, get_edges, get_nodes
from hopeit.apps_visualizer.visualization import VisualizationOptions, CytoscapeGraph
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages
from hopeit.app.api import event_api
from hopeit.dataobjects import dataclass, dataobject
from hopeit.app.events import collector_step, Collector

__steps__ = [
    'visualization_options',
    collector_step(payload=VisualizationOptions).gather(
        'config_graph',
        'cytoscape_data'
    ),
    'build_visualization'
]

__api__ = event_api(
    summary="App Visualizer: Events Diagram",
    description="Shows events, stream and data flow based on running configuration",
    query_args=[
        ("app_prefix", Optional[str], "app_key prefix to filter"),
        ("expand_queues", Optional[bool], "if `true` shows each stream queue as a separated stream")
    ],
    responses={
        200: (str, "HTML page with Events Graph")
    }
)

_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))


@dataobject
@dataclass
class EventsGraphResult:
    graph: CytoscapeGraph
    options: VisualizationOptions


async def visualization_options(payload: None, context: EventContext,
                                *, app_prefix: str = '',
                                expand_queues: bool = False) -> VisualizationOptions:
    return VisualizationOptions(
        app_prefix=app_prefix,
        expand_queues=expand_queues is True or expand_queues == 'true'
    )


async def config_graph(collector: Collector, context: EventContext) -> Graph:
    """
    Generates Graph object with nodes and edges from server runtime active configuration
    """
    options: VisualizationOptions = await collector['payload']
    app_prefix = options.app_prefix.replace('-', '_')
    server = getattr(sys.modules.get("hopeit.server.runtime"), "server")
    events = {}
    for app_key, app in server.app_engines.items():
        if app_prefix and app_key[0:len(app_prefix)] != app_prefix:
            continue

        app_config = app.app_config
        for event_name, event_info in app_config.events.items():
            impl = find_event_handler(app_config=app_config, event_name=event_name)
            splits = split_event_stages(app_config.app, event_name, event_info, impl)
            for name, info in splits.items():
                events[f"{app_key}.{name}"] = info

    nodes = get_nodes(events, expand_queues=options.expand_queues)
    edges = get_edges(nodes)
    return Graph(nodes=nodes, edges=edges)


async def cytoscape_data(collector: Collector, context: EventContext) -> CytoscapeGraph:
    """
    Converts Graph to cytoscape json format
    """
    def _edge_label(edge: Edge) -> str:
        label = edge.label.split('.')[-1]
        if label in ("AUTO", "POST", "GET", "MULTIPART"):
            return ""
        return label

    def _node_label(node: Node) -> str:
        comps = node.label.split(".")
        if len(comps) > 2:
            return '\n'.join(['.'.join(comps[0:2]), '.'.join(comps[2:])])
        return node.label

    graph: Graph = await collector['config_graph']

    nodes = [
        {"data": {
            "id": node.id,
            "content": _node_label(node),
        }, "classes": node.type.value}
        for node in graph.nodes
    ]
    edges = [
        {"data": {
            "id": f"edge_{edge.id}",
            "source": edge.source,
            "target": edge.target,
            "label": _edge_label(edge)
        }}
        for edge in graph.edges
    ]
    return CytoscapeGraph(data=[*nodes, *edges])


async def build_visualization(collector: Collector, context: EventContext) -> EventsGraphResult:
    return EventsGraphResult(
        graph=await collector['cytoscape_data'],
        options=await collector['payload']
    )


async def __postprocess__(result: EventsGraphResult, context: EventContext, response: PostprocessHook) -> str:
    """
    Renders html from template, using cytospace data json
    """
    response.set_content_type("text/html")

    expand_queues = f"events-graph{'' if result.options.expand_queues else '?expand_queues=true'}"
    expand_queues_label = f"{'Standard view' if result.options.expand_queues else 'Expanded view'}"

    with open(_dir_path / 'events_graph_template.html') as f:
        template = f.read()
        template = template.replace("{{expand_queues}}", expand_queues)
        template = template.replace("{{expand_queues_label}}", expand_queues_label)
        return template.replace("{{data}}", json.dumps(result.graph.data))
