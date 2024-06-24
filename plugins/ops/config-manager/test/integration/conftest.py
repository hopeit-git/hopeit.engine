import socket
import os
import json
from pathlib import Path
from typing import Dict

import pytest
from hopeit.app.config import EventDescriptor
from hopeit.server.version import APPS_API_VERSION, ENGINE_VERSION, APPS_ROUTE_VERSION
from hopeit.dataobjects.payload import Payload
from hopeit.config_manager import RuntimeApps, ServerStatus


EFFECTIVE_EVENTS_EXAMPLE = """
{
  "example_event$expanded": {
    "type": "POST",
    "plug_mode": "Standalone",
    "connections": [],
    "write_stream": {
      "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
      "queues": [
        "AUTO"
      ],
      "queue_strategy": "DROP"
    },
    "auth": []
  },
  "login$expanded": {
    "type": "GET",
    "plug_mode": "OnApp",
    "connections": [],
    "auth": [
      "Basic"
    ]
  }
}
"""


def _get_runtime_simple_example(url: str, source: str):
    with open(Path(__file__).parent / source) as f:
        res = f.read()
        res = res.replace("${HOST_NAME}", socket.gethostname())
        res = res.replace("${PID}", str(os.getpid()))
        res = res.replace("${URL}", url)
        res = res.replace("${ENGINE_VERSION}", ENGINE_VERSION)
        res = res.replace("${APPS_API_VERSION}", APPS_API_VERSION)
        res = res.replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)

    result = Payload.from_json(res, RuntimeApps)

    return result


@pytest.fixture
def runtime_apps_response():
    return _get_runtime_simple_example("in-process", source="runtime_simple_example.json")


@pytest.fixture
def server1_apps_response():
    return _get_runtime_simple_example("http://test-server1", source="runtime_simple_example.json")


@pytest.fixture
def server2_apps_response():
    return _get_runtime_simple_example("http://test-server2", source="runtime_simple_example.json")


@pytest.fixture
def effective_events_example():
    res = EFFECTIVE_EVENTS_EXAMPLE
    res = res.replace("${ENGINE_VERSION}", ENGINE_VERSION)
    res = res.replace("${APPS_API_VERSION}", APPS_API_VERSION)
    res = res.replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)
    res = json.loads(res)

    result = Payload.from_obj(res, datatype=Dict[str, EventDescriptor])

    return result


@pytest.fixture
def cluster_apps_response():
    server1 = _get_runtime_simple_example("http://test-server1", source="runtime_simple_example.json")
    server2 = _get_runtime_simple_example("http://test-server2", source="runtime_simple_example.json")

    server1.apps[f"simple_example.{APPS_ROUTE_VERSION}"].servers.extend(
        server2.apps[f"simple_example.{APPS_ROUTE_VERSION}"].servers
    )
    server1.apps[f"basic_auth.{APPS_ROUTE_VERSION}"].servers.extend(
        server2.apps[f"basic_auth.{APPS_ROUTE_VERSION}"].servers
    )
    server1.server_status["http://test-server2"] = ServerStatus.ALIVE

    return server1
