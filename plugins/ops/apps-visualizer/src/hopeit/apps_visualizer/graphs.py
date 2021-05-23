from typing import List, Dict
from dataclasses import dataclass, field
from enum import Enum

from hopeit.dataobjects import dataobject
from hopeit.app.config import EventType, EventConfig, StreamQueueStrategy


class NodeType(Enum):
    REQUEST = "REQUEST"
    EVENT = "EVENT"
    STREAM = "STREAM"


@dataobject
@dataclass
class Node:
    id: str
    label: str
    type: NodeType
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    slots: List[str] = field(default_factory=list)


@dataobject
@dataclass
class Edge:
    id: str
    label: str
    source: str
    target: str


@dataobject
@dataclass
class Graph:
    nodes: List[Node]
    edges: List[Edge]


def get_nodes(events: Dict[str, EventConfig], expand_queues: bool = True) -> Dict[str, Node]:
    nodes = {}
    for event_name, event_info in events.items():
        inputs, outputs = [], []
        if event_info.type in (EventType.GET, EventType.POST):
            port_name = f"{event_name}.{event_info.type.value}"
            inputs.append(port_name)
            request_node = Node(
                id=port_name, label=event_info.type.value, type=NodeType.REQUEST, outputs=[port_name]
            ) 
            nodes[port_name] = request_node
            
        if event_info.read_stream:
            queues = event_info.read_stream.queues
            for qid, queue in zip(queues, queues) if expand_queues else [("*", "|".join(queues))]:
                stream_id = f"{event_info.read_stream.name}.{qid}"
                stream_name = f"{event_info.read_stream.name}"
                stream_node = nodes.get(stream_id, Node(
                    id=stream_id, label=stream_name, type=NodeType.STREAM
                ))
                stream_node.slots = sorted(set([*stream_node.slots, *queue.split("|")]))
                nodes[stream_id] = stream_node
            
                for queue in [queue] if expand_queues else queues:
                    port_name = f"{event_name}.{stream_name}.{queue}"
                    inputs.append(port_name)
                    stream_node.outputs.append(port_name)

        if event_info.write_stream:
            queues = event_info.write_stream.queues
            if event_info.read_stream and event_info.write_stream.queue_strategy == StreamQueueStrategy.PROPAGATE:
                queues = [
                    qx if qy == "AUTO" else qy
                    for qx in event_info.read_stream.queues
                    for qy in queues
                ]
            for qid, queue in zip(queues, queues) if expand_queues else [("*", "|".join(queues))]:
                stream_id = f"{event_info.write_stream.name}.{qid}"
                stream_name = f"{event_info.write_stream.name}"
                
                stream_node = nodes.get(stream_id, Node(
                    id=stream_id, label=stream_name, type=NodeType.STREAM
                ))
                stream_node.slots = sorted(set([*stream_node.slots, *queue.split("|")]))
                nodes[stream_id] = stream_node
                
                for queue in [queue] if expand_queues else queues:
                    port_name = f"{event_name}.{stream_name}.{queue}"
                    stream_node.inputs.append(port_name)
                    outputs.append(port_name)

        nodes[event_name] = Node(
            id=event_name, label=event_name, type=NodeType.EVENT, inputs=inputs, outputs=outputs
        )

    return list(nodes.values())


def get_edges(nodes: List[Node]):
    inputs = {
        port: node for node in nodes for port in node.inputs
    }
    outputs = {
        port: node for node in nodes for port in node.outputs
    }

    edges = []
    for k, source in outputs.items():
        target = inputs.get(k)
        if target:
            edges.append(Edge(
                id=k,
                label=k.split(".")[-1],
                source=source.id,
                target=target.id
            ))
            
    return edges
