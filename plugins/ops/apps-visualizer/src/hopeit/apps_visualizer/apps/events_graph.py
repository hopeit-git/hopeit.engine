"""
Events graph showing events, stream and dependecies for specified apps
"""
import sys
import asyncio
from typing import List, Optional
from datetime import datetime, timezone

from hopeit.app.context import EventContext

from hopeit.server.imports import find_event_handler
from hopeit.server.steps import split_event_stages
from hopeit.app.api import event_api
from hopeit.dataobjects import dataclass, dataobject
from hopeit.app.events import collector_step, Collector
from hopeit.app.config import AppConfig
from hopeit.app.logger import app_extra_logger

from hopeit.config_manager import RuntimeApps
from hopeit.config_manager.client import get_apps_config

from hopeit.apps_visualizer.apps import get_runtime_apps
from hopeit.apps_visualizer.graphs import Edge, Node, Graph, get_edges, get_nodes
from hopeit.apps_visualizer.site.visualization import CytoscapeGraph, VisualizationOptions, visualization_options, visualization_options_api_args  # noqa: F401

logger, extra = app_extra_logger()

__steps__ = [
    'visualization_options',
    collector_step(payload=VisualizationOptions).gather(
        'runtime_apps',
        'config_graph',
        'cytoscape_data'
    ),
    'build_visualization'
]


# @dataobject
# @dataclass
# class RuntimeApps:
#     apps: List[AppConfig]


@dataobject
@dataclass
class EventsGraphResult:
    runtime_apps: RuntimeApps
    graph: CytoscapeGraph
    options: VisualizationOptions


__api__ = event_api(
    summary="App Visualizer: Events Graph Data",
    description="App Visualizer: Events Graph Data",
    query_args=visualization_options_api_args(),
    responses={
        200: (EventsGraphResult, "Graph Data with applied Live Stats")
    }
)


async def runtime_apps(collector: Collector, context: EventContext) -> RuntimeApps:
    """
    Extract current runtime app_config objects
    """
    return await get_runtime_apps(context)


async def config_graph(collector: Collector, context: EventContext) -> Optional[Graph]:
    """
    Generates Graph object with nodes and edges from server runtime active configuration
    """
    options: VisualizationOptions = await collector['payload']
    all_apps: RuntimeApps = await collector['runtime_apps']
    filterd_apps = (
        runtime_info.app_config for app_key, runtime_info in all_apps.apps.items()
        if (options.app_prefix == '' or (
            runtime_info.app_config.app.name[0:len(options.app_prefix)] == options.app_prefix
        )) and (options.host_filter == '' or
            any(options.host_filter in server.url for server in runtime_info.servers)
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
