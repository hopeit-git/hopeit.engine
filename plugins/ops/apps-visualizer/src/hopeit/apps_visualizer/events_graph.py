"""
Events graph showing events, stream and dependecies for specified apps
"""
import sys

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.graphs import Graph, get_edges, get_nodes
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages

__steps__ = ['generate_config_graph']


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


async def __postprocess__(graph: Graph, context: EventContext, response: PostprocessHook) -> str:
    # TODO: Read template, build graph data and return text/html response
    # TODO: Support change content-type: response.set_header("content-type", "text/html")
    return """
    <html>
    <h1> Apps! </h1>
    <body>
    {}
    </body>
    <html>
    """.format(graph.to_json())
