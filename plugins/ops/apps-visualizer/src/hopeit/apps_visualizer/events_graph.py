"""
Events graph showing events, stream and dependecies for specified apps
"""
import os
import sys
from typing import Optional
import json
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.graphs import Edge, Node, GraphDocument, get_edges, get_nodes
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages
from hopeit.app.api import event_api

__steps__ = ['generate_config_graph', 'build_cytoscape_data']

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


async def generate_config_graph(payload: None, context: EventContext,
                                *, app_prefix: str = '',
                                expand_queues: bool = False) -> GraphDocument:
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
    return GraphDocument(nodes=nodes, edges=edges, expanded_queues=(expand_queues is True or expand_queues == 'true'))


async def build_cytoscape_data(graph: GraphDocument, context: EventContext) -> GraphDocument:
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

    # node_index = {node.1id: node for node in graph.nodes}
    nodes = [
        {"data": {
            "group": node.type.value,
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
    graph.data = [*nodes, *edges]
    return graph


async def __postprocess__(graph: GraphDocument, context: EventContext, response: PostprocessHook) -> str:
    """
    Renders html from template, using cytospace data json
    """
    response.set_content_type("text/html")

    expand_queues = f"events-graph{'' if graph.expanded_queues else '?expand_queues=true'}"
    expand_queues_label = f"{'Standard view' if graph.expanded_queues else 'Expanded view'}"

    with open(_dir_path / 'events_graph_template.html') as f:
        template = f.read()
        template = template.replace("{{expand_queues}}", expand_queues)
        template = template.replace("{{expand_queues_label}}", expand_queues_label)
        return template.replace("{{data}}", json.dumps(graph.data))
