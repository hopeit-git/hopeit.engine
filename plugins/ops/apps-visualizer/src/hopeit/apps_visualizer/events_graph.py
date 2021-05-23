"""
Events graph showing events, stream and dependecies for specified apps
"""
import os
import sys
import json
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.graphs import Graph, get_edges, get_nodes
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages

__steps__ = ['generate_config_graph', 'build_cytoscape_data']

_dir_path = Path(os.path.dirname(os.path.realpath(__file__)))


async def generate_config_graph(payload: None, context: EventContext) -> Graph:
    server = getattr(sys.modules.get("hopeit.server.runtime"), "server")
    events = {}
    for app_key, app in server.app_engines.items():
        app_config = app.app_config
        for event_name, event_info in app_config.events.items():
            impl = find_event_handler(app_config=app_config, event_name=event_name)
            splits = split_event_stages(app_config.app, event_name, event_info, impl)
            for name, info in splits.items():
                events[f"{app_key}.{name}"] = info

    nodes = get_nodes(events, expand_queues=False)
    edges = get_edges(nodes)
    return Graph(nodes=nodes, edges=edges)


def build_cytoscape_data(graph: Graph, context: EventContext) -> str:
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
        {   "data": {
            "id": f"edge_{edge.id}",
            "source": edge.source,
            "target": edge.target,
            "label": edge.label.split('.')[-1]
        }}
        for edge in graph.edges
    ]
    data = [*nodes, *edges]
    return json.dumps(data)


async def __postprocess__(data: str, context: EventContext, response: PostprocessHook) -> str:
    # TODO: Read template, build graph data and return text/html response
    with open(_dir_path / 'events_graph_template.html') as f:
        template = f.read()
        response.set_content_type("text/html")
        return template.replace("{ data }", data)
