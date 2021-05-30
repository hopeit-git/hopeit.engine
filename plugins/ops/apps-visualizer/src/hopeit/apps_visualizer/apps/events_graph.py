"""
Events graph showing events, stream and dependecies for specified apps
"""
import os
import sys
from typing import List, Optional
import json
from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

from hopeit.apps_visualizer.graphs import Edge, Node, Graph, get_edges, get_nodes
from hopeit.apps_visualizer.site.visualization import VisualizationOptions, CytoscapeGraph, \
    visualization_options
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages
from hopeit.app.api import event_api
from hopeit.dataobjects import dataclass, dataobject
from hopeit.app.events import collector_step, Collector
from hopeit.app.config import AppConfig

__steps__ = [
    'visualization_options',
    collector_step(payload=VisualizationOptions).gather(
        'runtime_apps',
        'config_graph',
        'cytoscape_data'
    ),
    'build_visualization'
]


@dataobject
@dataclass
class RuntimeApps:
    apps: List[AppConfig]


@dataobject
@dataclass
class EventsGraphResult:
    runtime_apps: RuntimeApps
    graph: CytoscapeGraph
    options: VisualizationOptions


__api__ = event_api(
    summary="App Visualizer: Events Graph Data",
    description="App Visualizer: Events Graph Data",
    query_args=[
        ("app_prefix", Optional[str], "app_key prefix to filter"),
        ("expand_queues", Optional[bool], "if `true` shows each stream queue as a separated stream")
    ],
    responses={
        200: (EventsGraphResult, "Graph Data with applied Live Stats")
    }
)


async def runtime_apps(collector: Collector, context: EventContext) -> RuntimeApps:
    """
    Extract current runtime app_config objects
    """
    server = getattr(sys.modules.get("hopeit.server.runtime"), "server")
    return RuntimeApps(
        apps=sorted(
            (app.app_config for app in server.app_engines.values()),
            key=lambda x: x.app_key()
        )
    )


async def config_graph(collector: Collector, context: EventContext) -> Graph:
    """
    Generates Graph object with nodes and edges from server runtime active configuration
    """
    options: VisualizationOptions = await collector['payload']
    all_apps: RuntimeApps = await collector['runtime_apps']
    filterd_apps = (
        app_config for app_config in all_apps.apps
        if options.app_prefix == '' or (
            app_config.app.name[0:len(options.app_prefix)] == options.app_prefix
        )
    )

    events = {}
    for app_config in filterd_apps:
        for event_name, event_info in app_config.events.items():
            impl = find_event_handler(app_config=app_config, event_name=event_name)
            splits = split_event_stages(app_config.app, event_name, event_info, impl)
            for name, info in splits.items():
                events[f"{app_config.app_key()}.{name}"] = info

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

    nodes = {
        node.id: {"data": {
            "id": node.id,
            "content": _node_label(node),
        }, "classes": node.type.value}
        for node in graph.nodes
    }
    edges = {
        f"edge_{edge.id}": {"data": {
            "id": f"edge_{edge.id}",
            "source": edge.source,
            "target": edge.target,
            "label": _edge_label(edge)
        }}
        for edge in graph.edges
    }
    return CytoscapeGraph(data={**nodes, **edges})


async def build_visualization(collector: Collector, context: EventContext) -> EventsGraphResult:
    return EventsGraphResult(
        runtime_apps=await collector['runtime_apps'],
        graph=await collector['cytoscape_data'],
        options=await collector['payload']
    )
