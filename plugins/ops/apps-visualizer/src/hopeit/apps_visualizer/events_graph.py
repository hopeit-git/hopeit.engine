"""
Events graph showing events, stream and dependecies for specified apps
"""
import os
import sys
from typing import Optional
import json
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.graphs import Edge, Graph, get_edges, get_nodes
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages
from hopeit.app.api import event_api

__steps__ = ['generate_config_graph', 'build_cytoscape_data']

__api__ = event_api(
    summary="App Visualizer: Events Diagram",
    description="Shows events, stream and data flow based on running configuration",
    query_args=[
        ("app_prefix", Optional[str], "app_key prefix to filter"),
        ("expand_queus", Optional[bool], "if `true` shows each stream queue as a separated stream")
    ],
    responses={
        200: (str, "HTML page with Events Graph")
    }
)

_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))


async def generate_config_graph(payload: None, context: EventContext,
                                *, app_prefix: str = '',
                                expand_queues: bool = False) -> Graph:
    """
    Generates Graph object with nodes and edges from server runtime active configuration
    """
    app_prefix = app_prefix.replace('-', '_')
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

    nodes = get_nodes(
        events, expand_queues=(expand_queues is True or expand_queues == 'true')
    )
    edges = get_edges(nodes)
    return Graph(nodes=nodes, edges=edges)


async def build_cytoscape_data(graph: Graph, context: EventContext) -> str:
    """
    Converts Graph to cytoscape json format
    """
    def _edge_label(edge: Edge) -> str:
        label = edge.label.split('.')[-1]
        if label in (edge.source.split('.')[-1], "AUTO"):
            return ""
        return label

    # node_index = {node.id: node for node in graph.nodes}
    nodes = [
        {"data": {
            "group": node.type.value,
            "id": node.id,
            "content": '\n'.join(node.label.split('.'))
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
    data = [*nodes, *edges]
    return json.dumps(data)


async def __postprocess__(data: str, context: EventContext, response: PostprocessHook) -> str:
    """
    Renders html from template, using cytospace data json
    """
    with open(_dir_path / 'events_graph_template.html') as f:
        template = f.read()
        response.set_content_type("text/html")
        return template.replace("{{data}}", data)
