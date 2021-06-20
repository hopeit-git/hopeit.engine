import pytest

from hopeit.dataobjects.jsonify import Json

from hopeit.log_streamer import LogBatch, LogRawBatch, LogReaderConfig
import uuid
from hopeit.testing.apps import config, create_test_context

from . import APP_VERSION, APPS_API_VERSION


@pytest.fixture
def raw_log_entries() -> LogRawBatch:
    return LogRawBatch(data=[
        f"2021-06-02 18:01:44,290 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,294 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | __init_event__ module=simple_example.query_something... | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,295 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | load | extra.something_id=1 | extra.path=/tmp/simple_example.{APP_VERSION}.fs.data_path | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,298 | WARNING | simple-example {APPS_API_VERSION} query_something host 17031 | item not found | extra.something_id=1 | extra.path=/tmp/simple_example.{APP_VERSION}.fs.data_path | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:01:44,303 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test"  # noqa: E501
    ])


@pytest.fixture
def raw_log_entries2() -> LogRawBatch:
    return LogRawBatch(data=[
        f"2021-06-02 18:02:44,290 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:02:44,294 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | __init_event__ module=simple_example.query_something... | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:02:44,295 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | load | extra.something_id=1 | extra.path=/tmp/simple_example.{APP_VERSION}.fs.data_path | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:02:44,298 | WARNING | simple-example {APPS_API_VERSION} query_something host 17031 | item not found | extra.something_id=1 | extra.path=/tmp/simple_example.{APP_VERSION}.fs.data_path | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",  # noqa: E501
        f"2021-06-02 18:02:44,303 | INFO | simple-example {APPS_API_VERSION} query_something host 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test"  # noqa: E501
    ])


@pytest.fixture
def expected_log_entries() -> LogBatch:
    return Json.from_json("""
{
  "entries": [
    {
      "ts": "2021-06-02 18:01:44,290",
      "msg": "START",
      "app_name": "simple-example",
      "app_version": "${APPS_API_VERSION}",
      "event_name": "query_something",
      "event": "simple_example.${APP_VERSION}.query_something",
      "extra": {
        "track.operation_id": "f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5",
        "track.request_id": "7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82",
        "track.request_ts": "2021-06-02T18:01:44.289394+00:00",
        "track.caller": "test",
        "track.session_id": "test"
      },
      "host": "host",
      "pid": "17031"
    },
    {
      "ts": "2021-06-02 18:01:44,303",
      "msg": "DONE",
      "app_name": "simple-example",
      "app_version": "${APPS_API_VERSION}",
      "event_name": "query_something",
      "event": "simple_example.${APP_VERSION}.query_something",
      "extra": {
        "response.status": "404",
        "metrics.duration": "13.057",
        "track.operation_id": "f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5",
        "track.request_id": "7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82",
        "track.request_ts": "2021-06-02T18:01:44.289394+00:00",
        "track.caller": "test",
        "track.session_id": "test"
      },
      "host": "host",
      "pid": "17031"
    }
  ]
}
""".replace("${APPS_API_VERSION}", APPS_API_VERSION).replace("${APP_VERSION}", APP_VERSION), LogBatch)


@pytest.fixture
def log_config():
    return LogReaderConfig(
        logs_path="/tmp/test_it_log_file_handler/",
        prefix=f"{str(uuid.uuid4())}.log",
        checkpoint_path='/tmp/test_it_log_file_handler/log_streamer/checkpoints/',
        file_open_timeout_secs=600,
        file_checkpoint_expire_secs=86400,
        batch_size=100,
        batch_wait_interval_secs=1
    )


@pytest.fixture
def context():
    app_config = config('plugins/ops/log-streamer/config/plugin-config.json')
    return create_test_context(app_config, "log_reader")
