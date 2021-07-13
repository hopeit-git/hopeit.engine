import json
import os
from pathlib import Path
from datetime import datetime

import pytest
from hopeit.app.config import EventDescriptor
from hopeit.dataobjects.payload import Payload

from hopeit.server.version import APPS_API_VERSION, APPS_ROUTE_VERSION
from hopeit.server import config as server_config
from hopeit.testing.apps import config, execute_event

from hopeit.log_streamer import LogRawBatch, LogBatch
from hopeit.config_manager.runtime import runtime

from . import MockServer
from hopeit.config_manager import RuntimeAppInfo, RuntimeApps, ServerInfo, ServerStatus
import socket


EFFECTIVE_EVENTS_SIMPLE_EXAMPLE = """
{
        "list_somethings": {
          "type": "GET",
          "plug_mode": "Standalone",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "query_something": {
          "type": "GET",
          "plug_mode": "Standalone",
          "route": "simple-example/${APPS_API_VERSION}/query_something",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "query_something_extended": {
          "type": "POST",
          "plug_mode": "Standalone",
          "route": "simple-example/${APPS_API_VERSION}/query_something",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "save_something": {
          "type": "POST",
          "plug_mode": "Standalone",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "download_something": {
          "type": "GET",
          "plug_mode": "Standalone",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "upload_something": {
          "type": "MULTIPART",
          "plug_mode": "Standalone",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "service.something_generator": {
          "type": "SERVICE",
          "plug_mode": "Standalone",
          "connections": [],
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "DROP"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 10,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "streams.something_event": {
          "type": "POST",
          "plug_mode": "Standalone",
          "connections": [],
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
            "queues": [
              "high-prio"
            ],
            "queue_strategy": "DROP"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "streams.process_events": {
          "type": "STREAM",
          "plug_mode": "Standalone",
          "connections": [],
          "read_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
            "consumer_group": "simple_example.${APPS_ROUTE_VERSION}.streams.process_events",
            "queues": [
              "high-prio",
              "AUTO"
            ]
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group",
                "stream.event_id",
                "stream.event_ts",
                "stream.submit_ts",
                "stream.read_ts"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 5,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "collector.query_concurrently": {
          "type": "POST",
          "plug_mode": "Standalone",
          "connections": [],
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 0,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "collector.collect_spawn": {
          "type": "POST",
          "plug_mode": "Standalone",
          "connections": [],
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.collector.collect_spawn.collector@load_first",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "PROPAGATE"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "collector.collect_spawn$spawn": {
          "type": "STREAM",
          "plug_mode": "Standalone",
          "connections": [],
          "read_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.collector.collect_spawn.collector@load_first",
            "consumer_group": "simple_example.${APPS_ROUTE_VERSION}.collector.collect_spawn.spawn",
            "queues": [
              "AUTO"
            ]
          },
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "DROP"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "shuffle.spawn_event": {
          "type": "POST",
          "plug_mode": "Standalone",
          "connections": [],
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.shuffle.spawn_event.spawn_many_events",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "PROPAGATE"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "shuffle.spawn_event$update_status": {
          "type": "STREAM",
          "plug_mode": "Standalone",
          "connections": [],
          "read_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.shuffle.spawn_event.spawn_many_events",
            "consumer_group": "simple_example.${APPS_ROUTE_VERSION}.shuffle.spawn_event.update_status",
            "queues": [
              "AUTO"
            ]
          },
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "DROP"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "shuffle.parallelize_event": {
          "type": "POST",
          "plug_mode": "Standalone",
          "connections": [],
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.shuffle.parallelize_event.fork_something",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "PROPAGATE"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "shuffle.parallelize_event$process_first_part": {
          "type": "STREAM",
          "plug_mode": "Standalone",
          "connections": [],
          "read_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.shuffle.parallelize_event.fork_something",
            "consumer_group": "simple_example.${APPS_ROUTE_VERSION}.shuffle.parallelize_event.process_first_part",
            "queues": [
              "AUTO"
            ]
          },
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.shuffle.parallelize_event.process_first_part",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "PROPAGATE"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        },
        "shuffle.parallelize_event$update_status": {
          "type": "STREAM",
          "plug_mode": "Standalone",
          "connections": [],
          "read_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.shuffle.parallelize_event.process_first_part",
            "consumer_group": "simple_example.${APPS_ROUTE_VERSION}.shuffle.parallelize_event.update_status",
            "queues": [
              "AUTO"
            ]
          },
          "write_stream": {
            "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
            "queues": [
              "AUTO"
            ],
            "queue_strategy": "DROP"
          },
          "config": {
            "response_timeout": 60.0,
            "logging": {
              "extra_fields": [
                "something_id"
              ],
              "stream_fields": [
                "stream.name",
                "stream.msg_id",
                "stream.consumer_group"
              ]
            },
            "stream": {
              "timeout": 60.0,
              "target_max_len": 1000,
              "throttle_ms": 0,
              "step_delay": 0,
              "batch_size": 100,
              "compression": "lz4",
              "serialization": "json+base64"
            }
          },
          "auth": []
        }
      }
"""


def mock_getenv(var_name):
    if var_name == "HOPEIT_APPS_VISUALIZER_HOSTS":
        return "in-process"
    if var_name == "HOPEIT_SIMPLE_EXAMPLE_HOSTS":
        return "test-host"
    if var_name == "HOPEIT_APPS_API_VERSION":
        return APPS_API_VERSION
    if var_name == "HOPEIT_APPS_ROUTE_VERSION":
        return APPS_ROUTE_VERSION
    raise NotImplementedError(var_name)


@pytest.fixture
def runtime_apps(monkeypatch):
    monkeypatch.setattr(server_config.os, 'getenv', mock_getenv)
    app_config = config('apps/examples/simple-example/config/app-config.json')
    client_app_config = config('apps/examples/client-example/config/app-config.json')
    monkeypatch.setattr(
        runtime,
        "server",
        MockServer(
            app_config, client_app_config
        )
    )
    effective_events = {
        event_name: Payload.from_obj(event_info, datatype=EventDescriptor)
        for event_name, event_info in json.loads(EFFECTIVE_EVENTS_SIMPLE_EXAMPLE).items()
    } 
    return RuntimeApps(
        apps={
            app_config.app_key(): RuntimeAppInfo(
                servers=[
                    ServerInfo(
                        host_name=socket.gethostname(),
                        pid=str(os.getpid()),
                        url="in-process"
                    )
                ],
                app_config=app_config,
                effective_events=effective_events
            ),
            client_app_config.app_key(): RuntimeAppInfo(
                servers=[
                    ServerInfo(
                        host_name=socket.gethostname(),
                        pid=str(os.getpid()),
                        url="in-process"
                    )
                ],
                app_config=client_app_config,
                effective_events=client_app_config.events
            )
        },
        server_status={
            "in-process": ServerStatus.ALIVE
        }
    )


@pytest.fixture
def plugin_config(monkeypatch):
    monkeypatch.setattr(server_config.os, 'getenv', mock_getenv)
    return config('plugins/ops/apps-visualizer/config/plugin-config.json')


@pytest.fixture
def events_graph_data_standard():
    with open(Path(os.path.dirname(os.path.realpath(__file__))) / 'events_graph_data_standard.json') as f:
        json_str = f.read().replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)
        return json.loads(json_str)


@pytest.fixture
def events_graph_data_expanded():
    with open(Path(os.path.dirname(os.path.realpath(__file__))) / 'events_graph_data_expanded.json') as f:
        json_str = f.read().replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)
        return json.loads(json_str)


async def _process_log_entries(raw: LogRawBatch) -> LogBatch:
    plugin_config = config('plugins/ops/log-streamer/config/plugin-config.json')
    return await execute_event(plugin_config, "log_reader", payload=raw)  # type: ignore


@pytest.fixture
async def log_entries() -> LogBatch:
    raw = LogRawBatch(data=[
        f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} save_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} service.something_generator host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test |  stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event | stream.queue=AUTO",  # noqa: E501
        f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} service.something_generator host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event | stream.queue=AUTO",  # noqa: E501
        f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} streams.something_event host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test |  stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
        f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} streams.something_event host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
        f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} streams.process_events host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test | stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
        f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} streams.process_events host 17031 | FAILED | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test |  stream.name=simple_example.{APPS_ROUTE_VERSION}.streams.something_event.high-prio | stream.queue=high-prio",  # noqa: E501
    ])
    batch = await _process_log_entries(raw)
    ts = datetime.now()
    for entry in batch.entries:
        entry.ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        entry.host = socket.gethostname()
        entry.pid = str(os.getpid())
    return batch
