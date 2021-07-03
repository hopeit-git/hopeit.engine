import pytest

from hopeit.dataobjects.payload import Payload
from hopeit.config_manager import RuntimeApps, ServerStatus
import socket
import os

from hopeit.server.version import APPS_API_VERSION, ENGINE_VERSION, APPS_ROUTE_VERSION


RUNTIME_SIMPLE_EXAMPLE = """
{
  "apps": {
    "simple_example.${APPS_ROUTE_VERSION}": {
      "servers": [
        {
          "host_name": "${HOST_NAME}",
          "pid": "${PID}",
          "url": "${URL}"
        }
      ],
      "app_config": {
        "app": {
          "name": "simple-example",
          "version": "${APPS_API_VERSION}"
        },
        "engine": {
          "import_modules": [
            "simple_example"
          ],
          "read_stream_timeout": 1000,
          "read_stream_interval": 1000,
          "default_stream_compression": "lz4",
          "default_stream_serialization": "json+base64",
          "track_headers": [
            "track.request_id",
            "track.request_ts",
            "track.caller",
            "track.session_id"
          ],
          "cors_origin": "*"
        },
        "env": {
          "fs": {
            "data_path": "/tmp/simple_example.${APPS_ROUTE_VERSION}.fs.data_path/"
          },
          "upload_something": {
            "save_path": "/tmp/simple_example.${APPS_ROUTE_VERSION}.upload_something.save_path/",
            "chunk_size": 16384
          }
        },
        "events": {
          "list_somethings": {
            "type": "GET",
            "plug_mode": "Standalone",
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "write_stream": {
              "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
              "queues": [
                "AUTO"
              ],
              "queue_strategy": "DROP"
            },
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "write_stream": {
              "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
              "queues": [
                "high-prio"
              ],
              "queue_strategy": "DROP"
            },
            "config": {
              "response_timeout": 60,
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
                "timeout": 60,
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
            "read_stream": {
              "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
              "consumer_group": "simple_example.${APPS_ROUTE_VERSION}.streams.process_events",
              "queues": [
                "high-prio",
                "AUTO"
              ]
            },
            "config": {
              "response_timeout": 60,
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
                "timeout": 60,
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
            "config": {
              "response_timeout": 60,
              "logging": {
                "extra_fields": [],
                "stream_fields": [
                  "stream.name",
                  "stream.msg_id",
                  "stream.consumer_group"
                ]
              },
              "stream": {
                "timeout": 60,
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
            "write_stream": {
              "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
              "queues": [
                "AUTO"
              ],
              "queue_strategy": "DROP"
            },
            "config": {
              "response_timeout": 60,
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
                "timeout": 60,
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
            "write_stream": {
              "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
              "queues": [
                "AUTO"
              ],
              "queue_strategy": "DROP"
            },
            "config": {
              "response_timeout": 60,
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
                "timeout": 60,
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
            "write_stream": {
              "name": "simple_example.${APPS_ROUTE_VERSION}.streams.something_event",
              "queues": [
                "AUTO"
              ],
              "queue_strategy": "DROP"
            },
            "config": {
              "response_timeout": 60,
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
                "timeout": 60,
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
        },
        "server": {
          "streams": {
            "stream_manager": "hopeit.streams.NoStreamManager",
            "connection_str": "<<NoStreamManager>>",
            "delay_auto_start_seconds": 3
          },
          "logging": {
            "log_level": "DEBUG",
            "log_path": "logs/"
          },
          "auth": {
            "secrets_location": "",
            "auth_passphrase": "",
            "enabled": false,
            "create_keys": false,
            "encryption_algorithm": "RS256",
            "default_auth_methods": [
              "Unsecured"
            ]
          },
          "api": {},
          "engine_version": "${ENGINE_VERSION}"
        },
        "plugins": [
          {
            "name": "basic-auth",
            "version": "${APPS_API_VERSION}"
          }
        ]
      }
    }
  },
  "server_status": {
    "${URL}": "ALIVE"
  }
}
"""


def _get_runtime_simple_example(url: str):
    res = RUNTIME_SIMPLE_EXAMPLE
    res = res.replace("${HOST_NAME}", socket.gethostname())
    res = res.replace("${PID}", str(os.getpid()))
    res = res.replace("${URL}", url)
    res = res.replace("${ENGINE_VERSION}", ENGINE_VERSION)
    res = res.replace("${APPS_API_VERSION}", APPS_API_VERSION)
    res = res.replace("${APPS_ROUTE_VERSION}", APPS_ROUTE_VERSION)

    return Payload.from_json(res, RuntimeApps)


@pytest.fixture
def runtime_apps_response():
    return _get_runtime_simple_example("in-process")


@pytest.fixture
def server1_apps_response():
    return _get_runtime_simple_example("http://test-server1")


@pytest.fixture
def server2_apps_response():
    return _get_runtime_simple_example("http://test-server2")


@pytest.fixture
def cluster_apps_response():
    server1 = _get_runtime_simple_example("http://test-server1")
    server2 = _get_runtime_simple_example("http://test-server2")

    server1.apps[f"simple_example.{APPS_ROUTE_VERSION}"].servers.extend(
        server2.apps[f"simple_example.{APPS_ROUTE_VERSION}"].servers
    )
    server1.server_status["http://test-server2"] = ServerStatus.ALIVE

    return server1
