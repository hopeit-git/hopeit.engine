import pytest

from hopeit.dataobjects.jsonify import Json

from hopeit.log_streamer import LogBatch, LogRawBatch


@pytest.fixture
def raw_log_entries() -> LogRawBatch:
    return LogRawBatch(data=[
        "2021-06-02 18:01:44,290 | INFO | simple-example 0.5 query_something leo-legion 17031 | START | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",
        "2021-06-02 18:01:44,294 | INFO | simple-example 0.5 query_something leo-legion 17031 | __init_event__ module=simple_example.query_something... | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",
        "2021-06-02 18:01:44,295 | INFO | simple-example 0.5 query_something leo-legion 17031 | load | extra.something_id=1 | extra.path=/tmp/simple_example.0x5.fs.data_path | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",
        "2021-06-02 18:01:44,298 | WARNING | simple-example 0.5 query_something leo-legion 17031 | item not found | extra.something_id=1 | extra.path=/tmp/simple_example.0x5.fs.data_path | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test",
        "2021-06-02 18:01:44,303 | INFO | simple-example 0.5 query_something leo-legion 17031 | DONE | response.status=404 | metrics.duration=13.057 | track.operation_id=f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5 | track.request_id=7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82 | track.request_ts=2021-06-02T18:01:44.289394+00:00 | track.caller=test | track.session_id=test"
    ])


@pytest.fixture
def expected_log_entries() -> LogBatch:
    return Json.from_json(
"""
    {
  "entries": [
    {
      "ts": "2021-06-02 18:01:44,290",
      "msg": "START",
      "app_name": "simple-example",
      "app_version": "0.5",
      "event_name": "query_something",
      "event": "simple_example.0x5.query_something",
      "extra": {
        "track.operation_id": "f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5",
        "track.request_id": "7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82",
        "track.request_ts": "2021-06-02T18:01:44.289394+00:00",
        "track.caller": "test",
        "track.session_id": "test"
      }
    },
    {
      "ts": "2021-06-02 18:01:44,303",
      "msg": "DONE",
      "app_name": "simple-example",
      "app_version": "0.5",
      "event_name": "query_something",
      "event": "simple_example.0x5.query_something",
      "extra": {
        "response.status": "404",
        "metrics.duration": "13.057",
        "track.operation_id": "f2659a30-5ac4-4dd4-b1f7-9a00db0bf7d5",
        "track.request_id": "7ee59fa7-c1e4-4a60-a79b-a25dbbd6cb82",
        "track.request_ts": "2021-06-02T18:01:44.289394+00:00",
        "track.caller": "test",
        "track.session_id": "test"
      }
    }
  ]
}
""", LogBatch)