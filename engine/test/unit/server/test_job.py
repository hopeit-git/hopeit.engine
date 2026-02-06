import io
import re
import sys
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from hopeit.app.config import AppConfig
from hopeit.dataobjects.payload import Payload
from hopeit.server import job, engine, runtime
from hopeit.server.config import ServerConfig
from mock_engine import MockAppEngine  # type: ignore
from mock_app import (  # type: ignore
    MockData,
    mock_app_config,
    mock_api_app_config,
    mock_client_app_config,
)
from mock_plugin import mock_plugin_config  # type: ignore


def _make_event_engine(app_config: AppConfig):
    preprocess_calls: List[Any] = []
    execute_calls: List[Any] = []
    postprocess_calls: List[Any] = []

    async def preprocess(*, context, query_args, payload, request):
        preprocess_calls.append((context, query_args, payload, request))
        return payload

    async def execute(*, context, query_args, payload):
        execute_calls.append((context, query_args, payload))
        return payload

    async def postprocess(*, context, payload, response):
        postprocess_calls.append((context, payload, response))
        return payload

    app_engine = MagicMock()
    app_engine.app_config = app_config
    app_engine.settings = app_config.effective_settings
    app_engine.preprocess = preprocess
    app_engine.execute = execute
    app_engine.postprocess = postprocess
    return app_engine, preprocess_calls, execute_calls, postprocess_calls


@pytest.fixture
def silent_event_logger(monkeypatch):
    def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(job.logger, "start", _noop)
    monkeypatch.setattr(job.logger, "done", _noop)
    monkeypatch.setattr(job.logger, "failed", _noop)
    monkeypatch.setattr(job.logger, "error", _noop)


def test_resolve_payload_reads_sources(monkeypatch, tmp_path):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text("payload", encoding="utf-8")
    assert job.resolve_payload(f"@{payload_path}") == "payload"

    monkeypatch.setattr(sys, "stdin", io.StringIO("stdin-payload"))
    assert job.resolve_payload("@-") == "stdin-payload"

    assert job.resolve_payload("raw") == "raw"

    with pytest.raises(ValueError, match="Payload file path missing"):
        job.resolve_payload("@")


def test_parse_track_ids_normalizes_and_casts():
    track_ids = job.parse_track_ids('{"foo": 1, "track.bar": "two", "none": null, "flag": true}')
    assert track_ids == {
        "track.foo": "1",
        "track.bar": "two",
        "track.none": "",
        "track.flag": "True",
    }


def test_parse_track_ids_rejects_empty_key():
    with pytest.raises(ValueError, match="track key cannot be empty"):
        job.parse_track_ids('{"": "x"}')


@pytest.mark.parametrize(
    "payload,match",
    [
        ("", "query-args payload is empty"),
        ("   ", "query-args payload is empty"),
        ("[]", "query-args payload must be a JSON object"),
        ('{"x": {"nested": 1}}', "query-args value for key 'x' must be a scalar"),
        (
            '["x"= {"nested": 1}}',
            re.escape(
                "Invalid query-args JSON payload: Expecting ',' delimiter: line 1 column 5 (char 4)"
            ),
        ),
    ],
)
def test_parse_query_args_invalid(payload, match):
    with pytest.raises(ValueError, match=match):
        job.parse_query_args(payload)


def test_parse_query_args_casts_scalars():
    assert job.parse_query_args('{"limit": 5, "active": true}') == {
        "limit": "5",
        "active": "True",
    }


def test_parse_args_reads_payload_track_and_query(tmp_path):
    payload_path = tmp_path / "payload.json"
    track_path = tmp_path / "track.json"
    query_path = tmp_path / "query.json"

    payload_path.write_text('{"hello": "world"}', encoding="utf-8")
    track_path.write_text('{"foo": 1, "track.bar": "two"}', encoding="utf-8")
    query_path.write_text('{"limit": 5, "active": true}', encoding="utf-8")

    result = job.parse_args(
        [
            "--config-files=one.json,two.json",
            "--event-name=app.event",
            f"--payload=@{payload_path}",
            f"--track=@{track_path}",
            f"--query-args=@{query_path}",
            "--start-streams",
            "--max-events=7",
        ]
    )

    assert result.config_files == ["one.json", "two.json"]
    assert result.event_name == "app.event"
    assert result.payload == '{"hello": "world"}'
    assert result.start_streams is True
    assert result.max_events == 7
    assert result.track_ids == {"track.foo": "1", "track.bar": "two"}
    assert result.query_args == {"limit": "5", "active": "True"}


def test_select_app_config_by_event_and_step(mock_app_config, mock_api_app_config):
    assert (
        job._select_app_config(
            [mock_app_config, mock_api_app_config],
            "mock_event$step",
        )
        is mock_app_config
    )
    with pytest.raises(ValueError, match="Event not found: missing_event"):
        assert (
            job._select_app_config(
                [mock_app_config, mock_api_app_config],
                "missing_event",
            )
            is mock_app_config
        )


def test_select_app_config_multiple_apps_raises(mock_app_config, mock_client_app_config):
    with pytest.raises(ValueError, match="found in multiple apps"):
        job._select_app_config([mock_app_config, mock_client_app_config], "mock_event")


def test_plugins_for_app_preserves_order(
    mock_app_config, mock_plugin_config, mock_client_app_config
):
    result = job._plugins_for_app(
        mock_app_config,
        [mock_app_config, mock_client_app_config, mock_plugin_config],
    )
    assert result == [mock_plugin_config]


def test_plugins_for_app_missing_plugin_raises(mock_app_config):
    with pytest.raises(ValueError, match="Missing plugin config"):
        job._plugins_for_app(mock_app_config, [mock_app_config])


def test_parse_payload_variants():
    payload = Payload.to_json(MockData("hello"))
    parsed, raw = job._parse_payload(payload, MockData)
    assert parsed == MockData("hello")
    assert raw == payload.encode()

    parsed, raw = job._parse_payload(payload, None)
    assert parsed is None
    assert raw == payload.encode()

    parsed, raw = job._parse_payload(None, None)
    assert parsed is None
    assert raw is None


def test_job_track_ids_includes_required_fields(mock_app_config):
    track_ids = job._job_track_ids(
        mock_app_config,
        "mock_event",
        {"track.request_id": "fixed", "track.custom": "value"},
    )

    assert track_ids["track.request_id"] == "fixed"
    assert track_ids["track.custom"] == "value"
    assert track_ids["track.client_app_key"] == mock_app_config.app_key()
    assert track_ids["track.client_event_name"] == "mock_event"
    assert "track.operation_id" in track_ids
    assert "track.request_ts" in track_ids


async def test_execute_event_runs_preprocess_execute_postprocess(
    monkeypatch, mock_app_config, silent_event_logger
):
    app_engine, preprocess_calls, execute_calls, postprocess_calls = _make_event_engine(
        mock_app_config
    )

    monkeypatch.setattr(job, "find_datatype_handler", lambda **_: MockData)
    payload = Payload.to_json(MockData("hello"))

    result = await job._execute_event(
        app_engine=app_engine,
        event_name="mock_post_event",
        event_info=mock_app_config.events["mock_post_event"],
        payload=payload,
        track_ids={"track.foo": "bar"},
        query_args={"limit": "1"},
    )

    assert result == MockData("hello")
    assert len(preprocess_calls) == 1
    context, query_args, parsed_payload, request = preprocess_calls[0]
    assert query_args == {"limit": "1"}
    assert parsed_payload == MockData("hello")
    assert "track.request_id" in context.track_ids
    assert "track.request_ts" in context.track_ids
    assert len(execute_calls) == 1
    assert len(postprocess_calls) == 1
    assert request.payload_raw == payload.encode()


async def test_execute_event_respects_preprocess_status(
    monkeypatch, mock_app_config, silent_event_logger
):
    async def preprocess(*, context, query_args, payload, request):
        request.set_status(400)
        return payload

    app_engine = MagicMock()
    app_engine.app_config = mock_app_config
    app_engine.settings = mock_app_config.effective_settings
    app_engine.preprocess = preprocess
    app_engine.execute = AsyncMock(side_effect=AssertionError("execute should not be called"))
    app_engine.postprocess = AsyncMock(
        side_effect=AssertionError("postprocess should not be called")
    )
    monkeypatch.setattr(job, "find_datatype_handler", lambda **_: None)

    result = await job._execute_event(
        app_engine=app_engine,
        event_name="mock_post_event",
        event_info=mock_app_config.events["mock_post_event"],
        payload="{}",
        track_ids=None,
        query_args=None,
    )

    assert result is None


async def test_run_job_executes_get_event(monkeypatch, mock_app_config, mock_plugin_config):
    server_config = ServerConfig()

    runtime.server = engine.Server()
    start_mock = AsyncMock(return_value=runtime.server)
    stop_mock = AsyncMock()
    monkeypatch.setattr(runtime.server, "start", start_mock)
    monkeypatch.setattr(runtime.server, "stop", stop_mock)
    monkeypatch.setattr(job, "_load_engine_config", lambda _: server_config)
    monkeypatch.setattr(
        job,
        "_load_app_config",
        lambda path: mock_app_config if path == "app.json" else mock_plugin_config,
    )
    monkeypatch.setattr(job, "_run_setup_events", AsyncMock())

    execute_mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(job, "_execute_event", execute_mock)
    monkeypatch.setattr(job, "AppEngine", MockAppEngine)

    result = await job.run_job(
        config_files=["server.json", "app.json", "plugin.json"],
        event_name="mock_event",
        payload='{"hello": "world"}',
        track_ids={"track.foo": "bar"},
        query_args={"limit": "1"},
    )

    assert result == {"ok": True}
    start_mock.assert_awaited_once_with(config=server_config)
    stop_mock.assert_awaited_once()
    assert mock_app_config.server is server_config
    assert "track.foo" in mock_app_config.engine.track_headers
    execute_mock.assert_awaited_once()


async def test_run_job_stream_with_payload_executes_event(
    monkeypatch, mock_app_config, mock_plugin_config
):
    server_config = ServerConfig()

    runtime.server = engine.Server()
    start_mock = AsyncMock(return_value=runtime.server)
    stop_mock = AsyncMock()
    monkeypatch.setattr(runtime.server, "start", start_mock)
    monkeypatch.setattr(runtime.server, "stop", stop_mock)
    monkeypatch.setattr(job, "_load_engine_config", lambda _: server_config)
    monkeypatch.setattr(
        job,
        "_load_app_config",
        lambda path: mock_app_config if path == "app.json" else mock_plugin_config,
    )
    monkeypatch.setattr(job, "_run_setup_events", AsyncMock())

    execute_mock = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(job, "_execute_event", execute_mock)
    monkeypatch.setattr(job, "AppEngine", MockAppEngine)

    result = await job.run_job(
        config_files=["server.json", "app.json", "plugin.json"],
        event_name="mock_stream_event",
        payload='{"hello": "world"}',
        track_ids=None,
        query_args={"ignored": "1"},
    )

    assert result == {"ok": True}
    execute_mock.assert_awaited_once()
    await_args = execute_mock.await_args
    assert "query_args" not in await_args.kwargs or await_args.kwargs["query_args"] is None
    stop_mock.assert_awaited_once()


async def test_run_job_stream_requires_start_streams(
    monkeypatch, mock_app_config, mock_plugin_config
):
    server_config = ServerConfig()

    runtime.server = engine.Server()
    start_mock = AsyncMock(return_value=runtime.server)
    stop_mock = AsyncMock()
    monkeypatch.setattr(runtime.server, "start", start_mock)
    monkeypatch.setattr(runtime.server, "stop", stop_mock)
    monkeypatch.setattr(job, "_load_engine_config", lambda _: server_config)
    monkeypatch.setattr(
        job,
        "_load_app_config",
        lambda path: mock_app_config if path == "app.json" else mock_plugin_config,
    )
    monkeypatch.setattr(job, "_run_setup_events", AsyncMock())
    monkeypatch.setattr(job, "_execute_event", AsyncMock())
    monkeypatch.setattr(job, "AppEngine", MockAppEngine)

    with pytest.raises(NotImplementedError, match="require --start-streams"):
        await job.run_job(
            config_files=["server.json", "app.json", "plugin.json"],
            event_name="mock_stream_event",
            payload=None,
            start_streams=False,
        )

    stop_mock.assert_awaited_once()


async def test_run_job_stream_reads_when_start_streams(
    monkeypatch, mock_app_config, mock_plugin_config
):
    server_config = ServerConfig()

    runtime.server = engine.Server()
    start_mock = AsyncMock(return_value=runtime.server)
    stop_mock = AsyncMock()
    monkeypatch.setattr(runtime.server, "start", start_mock)
    monkeypatch.setattr(runtime.server, "stop", stop_mock)
    monkeypatch.setattr(job, "_load_engine_config", lambda _: server_config)
    monkeypatch.setattr(
        job,
        "_load_app_config",
        lambda path: mock_app_config if path == "app.json" else mock_plugin_config,
    )
    monkeypatch.setattr(job, "_run_setup_events", AsyncMock())

    execute_mock = AsyncMock()
    monkeypatch.setattr(job, "_execute_event", execute_mock)
    monkeypatch.setattr(job, "AppEngine", MockAppEngine)

    result = await job.run_job(
        config_files=["server.json", "app.json", "plugin.json"],
        event_name="mock_stream_event",
        payload=None,
        start_streams=True,
        max_events=3,
    )

    assert result is None
    execute_mock.assert_not_awaited()
    app_engine = runtime.server.app_engines[mock_app_config.app_key()]
    assert app_engine.read_stream_calls == [
        {
            "event_name": "mock_stream_event",
            "max_events": 3,
            "stop_when_empty": True,
            "wait_start": False,
            "test_mode": False,
        }
    ]
    stop_mock.assert_awaited_once()


async def test_run_job_unsupported_event_type(monkeypatch, mock_app_config, mock_plugin_config):
    server_config = ServerConfig()

    runtime.server = engine.Server()
    start_mock = AsyncMock(return_value=runtime.server)
    stop_mock = AsyncMock()
    monkeypatch.setattr(runtime.server, "start", start_mock)
    monkeypatch.setattr(runtime.server, "stop", stop_mock)
    monkeypatch.setattr(job, "_load_engine_config", lambda _: server_config)
    monkeypatch.setattr(
        job,
        "_load_app_config",
        lambda path: mock_app_config if path == "app.json" else mock_plugin_config,
    )
    monkeypatch.setattr(job, "_run_setup_events", AsyncMock())
    monkeypatch.setattr(job, "AppEngine", MockAppEngine)

    with pytest.raises(NotImplementedError, match="Unsupported event type"):
        await job.run_job(
            config_files=["server.json", "app.json", "plugin.json"],
            event_name="mock_service_event",
            payload=None,
        )

    stop_mock.assert_awaited_once()
