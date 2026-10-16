import json
import logging
import os
import uuid

import aiohttp
import pytest
from aiohttp import ClientResponse
from aiohttp.web import Application

from hopeit.app import events as app_events
from hopeit.server import api, engine, runtime, web
from hopeit.server.web import (
    app_startup_hook,
    server_startup_hook,
    stream_startup_hook,
)
from mock_app import MockResult, mock_app_config, mock_event_setup  # type: ignore
from mock_engine import MockEventHandler, MockStreamManager
from mock_plugin import mock_plugin_config, plugin_setup  # type: ignore


async def call_get_mock_event(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "ok"},
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("X-Status") == "ok"
    result = (await res.read()).decode()
    assert result == '{"mock_event":"ok: ok"}'


async def call_get_mock_event_cors_allowed(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "ok"},
        headers={
            "X-Track-Session-Id": "test_session_id",
            "Origin": "http://test",
            "Host": "test",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("Access-Control-Allow-Origin") == "http://test"
    assert res.headers.get("Access-Control-Allow-Credentials") == "true"
    result = (await res.read()).decode()
    assert result == '{"mock_event":"ok: ok"}'


async def call_get_mock_event_cors_unknown(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "ok"},
        headers={
            "X-Track-Session-Id": "test_session_id",
            "Origin": "http://unknown",
            "Host": "test",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("Access-Control-Allow-Origin") is None
    assert res.headers.get("Access-Control-Allow-Credentials") is None
    assert res.cookies.get("Test-Cookie").value == "ok"
    result = (await res.read()).decode()
    assert result == '{"mock_event":"ok: ok"}'


async def call_get_mock_event_special_case(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "no-ok"},
        headers={"x-track-session-id": "test_session_id"},
    )
    assert res.status == 400
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.cookies.get("Test-Cookie").value == ""
    result = (await res.read()).decode()
    assert result == '{"mock_event":"not-ok: None"}'


async def call_get_fail_request(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "fail"},
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 500
    result = (await res.read()).decode()
    assert result == '{"msg":"Test for error","tb":["AssertionError: Test for error\\n"]}'


async def call_post_mock_event(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "ok"},
        data='{"value": "ok"}',
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert result == '{"value":"ok: ok","processed":true}'


async def call_post_mock_event_preprocess(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-post-preprocess",
        params={"query_arg1": "ok"},
        data='{"value": "ok"}',
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert result == '{"value":"ok: test_request_id"}'


async def call_post_mock_event_preprocess_no_datatype(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-post-preprocess-no-datatype",
        params={"query_arg1": "ok"},
        data="OK\n",
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert result == '{"value":"ok: test_request_id"}'


async def call_multipart_mock_event(client):
    os.makedirs("/tmp/call_multipart_mock_event/", exist_ok=True)
    with open("/tmp/call_multipart_mock_event/test_attachment", "wb") as f:  # noqa: ASYNC230 -- Small synchronous test fixture with controlled file lifetime.
        f.write(b"testdata")

    with (
        open("/tmp/call_multipart_mock_event/test_attachment", "rb") as attachment,  # noqa: ASYNC230 -- Small synchronous upload fixture.
        aiohttp.MultipartWriter("form-data", boundary=":") as mp,
    ):
        mp.append("value1", headers={"Content-Disposition": 'form-data; name="field1"'})
        mp.append_json(
            {"value": "value2"},
            headers={"Content-Disposition": 'form-data; name="field2"'},
        )
        mp.append(
            attachment,
            headers={
                "Content-Disposition": 'attachments; name="attachment"; filename="test_attachment"'
            },
        )

        res: ClientResponse = await client.post(
            "/api/mock-app/test/mock-multipart-event-test",
            params={"query_arg1": "ok"},
            data=mp,
            headers={
                "X-Track-Request-Id": "test_request_id",
                "X-Track-Session-Id": "test_session_id",
                "Content-Type": 'multipart/form-data; boundary=":"',
            },
        )
        assert res.status == 200
        assert res.headers.get("X-Track-Session-Id") == "test_session_id"
        assert res.headers.get("X-Track-Request-Id") == "test_request_id"
        result = (await res.read()).decode()
        assert result == '{"value":"field1=value1 field2=value2 attachment=test_attachment ok"}'


async def call_multipart_mock_event_plain_text_json(client):
    os.makedirs("/tmp/call_multipart_mock_event/", exist_ok=True)
    with open("/tmp/call_multipart_mock_event/test_attachment", "wb") as f:  # noqa: ASYNC230 -- Small synchronous test fixture with controlled file lifetime.
        f.write(b"testdata")

    with (
        open("/tmp/call_multipart_mock_event/test_attachment", "rb") as attachment,  # noqa: ASYNC230 -- Small synchronous upload fixture.
        aiohttp.MultipartWriter("form-data", boundary=":") as mp,
    ):
        mp.append("value1", headers={"Content-Disposition": 'form-data; name="field1"'})
        mp.append(
            '{"value": "value2"}',
            headers={"Content-Disposition": 'form-data; name="field2"'},
        )
        mp.append(
            attachment,
            headers={
                "Content-Disposition": 'attachments; name="attachment"; filename="test_attachment"'
            },
        )

        res: ClientResponse = await client.post(
            "/api/mock-app/test/mock-multipart-event-test",
            params={"query_arg1": "ok"},
            data=mp,
            headers={
                "X-Track-Request-Id": "test_request_id",
                "X-Track-Session-Id": "test_session_id",
                "Content-Type": 'multipart/form-data; boundary=":"',
            },
        )
        assert res.status == 200
        assert res.headers.get("X-Track-Session-Id") == "test_session_id"
        assert res.headers.get("X-Track-Request-Id") == "test_request_id"
        result = (await res.read()).decode()
        assert result == '{"value":"field1=value1 field2=value2 attachment=test_attachment ok"}'


async def call_multipart_mock_event_bad_request(client):
    with aiohttp.MultipartWriter("form-data", boundary=":") as mp:
        mp.append("value1", headers={"Content-Disposition": 'form-data; name="field1"'})
        mp.append("value2", headers={"Content-Disposition": 'form-data; name="field2"'})

        res: ClientResponse = await client.post(
            "/api/mock-app/test/mock-multipart-event-test",
            data=mp,
            params={"query_arg1": "bad form"},
            headers={
                "X-Track-Request-Id": "test_request_id",
                "X-Track-Session-Id": "test_session_id",
                "Content-Type": 'multipart/form-data; boundary=":"',
            },
        )
        assert res.status == 400


async def call_post_nopayload(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-post-nopayload",
        params={"query_arg1": "ok"},
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert result == '{"mock_post_nopayload":"ok: nopayload ok"}'


async def call_post_invalid_payload(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "ok"},
        data='{"value": invalid_json}',
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 400
    result = (await res.read()).decode().lower()
    assert "validation error" in result
    assert "invalid json" in result


async def call_post_fail_request(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-event-test",
        params={"query_arg1": "fail"},
        data='{"value": "ok"}',
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 500
    result = (await res.read()).decode()
    assert result == '{"msg":"Test for error","tb":["AssertionError: Test for error\\n"]}'


async def call_post_mock_collector(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-collector",
        params={},
        data='{"value": "ok"}',
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert (
        result == '{"value":'
        '"((ok+mock_collector+step1)&(ok+mock_collector+step2)+mock_collector+step3)",'
        '"processed":true}'
    )


async def call_get_mock_spawn_event(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-spawn-event",
        params={"payload": "ok"},
        data=None,
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert result == '{"value":"stream: ok.2"}'


async def call_get_mock_timeout_ok(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-timeout",
        params={"delay": 1},
        data=None,
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id") == "test_request_id"
    result = (await res.read()).decode()
    assert result == '{"mock_timeout":"ok"}'


async def call_get_mock_timeout_exceeded(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-timeout",
        params={"delay": 5},
        data=None,
        headers={
            "X-Track-Request-Id": "test_request_id",
            "X-Track-Session-Id": "test_session_id",
        },
    )
    assert res.status == 500
    result = (await res.read()).decode().lower()
    assert "response timeout exceeded seconds=2.0" in result


async def call_get_file_response(client):
    file_name = str(uuid.uuid4()) + ".txt"
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-file-response",
        params={"file_name": file_name},
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("Content-Disposition") == f'attachment; filename="{file_name}"'
    assert res.headers.get("Content-Type") == "text/plain"
    result = (await res.read()).decode()
    assert result == "mock_file_response test file_response"


async def call_get_stream_response(client):
    file_name = str(uuid.uuid4()) + ".txt"
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-stream-response",
        params={"file_name": file_name},
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("Content-Disposition") == f'attachment; filename="{file_name}"'
    assert res.headers.get("Content-Type") == "application/octet-stream"
    assert res.headers.get("Content-length") == "48"
    result = await res.read()
    assert result == b"TestDataTestDataTestDataTestDataTestDataTestData"


async def call_get_file_response_content_type(client):
    file_name = "binary.png"
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-file-response_content_type",
        params={"file_name": file_name},
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("Content-Disposition") == f'attachment; filename="{file_name}"'
    assert res.headers.get("Content-Type") == "image/png"
    result = (await res.read()).decode()
    assert result == file_name


async def call_get_mock_auth_event(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-auth",
        headers={
            "X-Track-Session-Id": "test_session_id",
            "Authorization": "Basic 1234567890==",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    result = (await res.read()).decode()
    assert result == '{"mock_auth":"ok"}'


async def call_get_mock_auth_event_malformed_authorization(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-auth",
        headers={
            "X-Track-Session-Id": "test_session_id",
            "Authorization": "BAD_AUTHORIZATION",
        },
    )
    assert res.status == 400
    result = (await res.read()).decode()
    assert json.loads(result) == {
        "msg": "Malformed Authorization",
        "tb": ["hopeit.app.errors.BadRequest: Malformed Authorization\n"],
    }


async def call_get_mock_auth_event_unauthorized(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-auth",
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 401
    result = (await res.read()).decode()
    assert result == '{"msg":"Unsecured","tb":["hopeit.app.errors.Unauthorized: Unsecured\\n"]}'


async def call_post_mock_auth_event(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-post-auth",
        data='{"value": "test_data"}',
        headers={
            "X-Track-Session-Id": "test_session_id",
            "Authorization": "Basic 1234567890==",
        },
    )
    assert res.status == 200
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    result = (await res.read()).decode()
    assert result == '{"mock_post_auth":"ok: test_data"}'


async def call_post_mock_auth_event_unauthorized(client):
    res: ClientResponse = await client.post(
        "/api/mock-app/test/mock-post-auth",
        data='{"value": "test_data"}',
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 401
    result = (await res.read()).decode()
    assert result == '{"msg":"Unsecured","tb":["hopeit.app.errors.Unauthorized: Unsecured\\n"]}'


async def call_get_plugin_event_on_app(client):
    res: ClientResponse = await client.get(
        "/api/mock-app/test/mock-plugin/test/plugin-event",
        headers={"X-Track-Session-Id": "test_session_id"},
    )
    assert res.status == 999
    assert res.headers.get("X-Track-Session-Id") == "test_session_id"
    assert res.headers.get("X-Track-Request-Id")
    assert res.headers.get("X-Track-Request-Ts")
    assert res.headers.get("PluginHeader") == "PluginHeaderValue"
    assert res.cookies.get("PluginCookie").value == "PluginCookieValue"
    result = (await res.read()).decode()
    assert result == '{"plugin_event":"PluginEvent.postprocess"}'


async def check_setup_event_on_start(client):
    assert mock_event_setup.initialized


async def check_plugin_setup_event_on_start(client):
    assert plugin_setup.initialized


async def call_start_stream(client):
    res = await client.get("/mgmt/mock-app/test/mock-stream-event/start")
    assert res.status == 200


async def call_start_service(client):
    res = await client.get("/mgmt/mock-app/test/mock-service-event/start")
    assert res.status == 200


async def call_stop_stream(client):
    res = await client.get("/mgmt/mock-app/test/mock-stream-event/stop")
    assert res.status == 200


async def call_stop_service(client):
    res = await client.get("/mgmt/mock-app/test/mock-service-event/stop")
    assert res.status == 200


@pytest.fixture
async def app_client(monkeypatch, mock_app_config, mock_plugin_config, aiohttp_client):
    app = Application()
    server = engine.Server()
    monkeypatch.setattr(web, "web_server", app)
    monkeypatch.setattr(runtime, "server", server)
    monkeypatch.setattr(app_events, "server", server)
    monkeypatch.setattr(MockStreamManager, "test_payload", MockResult("ok: ok"))
    monkeypatch.setattr(MockEventHandler, "test_track_ids", None)
    api.clear()
    clients = []

    async def create(*, streams=False):
        app.cleanup_ctx.append(web._engine_cleanup_context)
        app.on_startup.append(lambda app: server_startup_hook(mock_app_config.server))
        app.on_startup.append(lambda app: app_startup_hook(mock_plugin_config, []))
        app.on_startup.append(lambda app: app_startup_hook(mock_app_config, []))
        if streams:
            app.on_startup.append(lambda app: stream_startup_hook(mock_app_config))
        client = await aiohttp_client(app)
        clients.append(client)
        return client

    try:
        yield create
    finally:
        for client in reversed(clients):
            await client.close()
        # Cleanup contexts also run if application startup failed before a client
        # could be returned by pytest-aiohttp.
        await app.cleanup()
        await server.stop()
        assert all(not app_engine._event_tasks for app_engine in server.app_engines.values())


@pytest.mark.order(1)
async def test_endpoints(
    app_client,
):
    test_client = await app_client()

    logger = logging.getLogger()

    test_list = [
        check_setup_event_on_start,
        check_plugin_setup_event_on_start,
        call_get_mock_event,
        call_get_mock_event_cors_allowed,
        call_get_mock_event_cors_unknown,
        call_get_mock_event_special_case,
        call_post_invalid_payload,
        call_post_mock_collector,
        call_get_mock_timeout_ok,
        call_get_mock_timeout_exceeded,
        call_get_fail_request,
        call_get_mock_spawn_event,
        call_post_mock_event,
        call_post_mock_event_preprocess,
        call_post_mock_event_preprocess_no_datatype,
        call_multipart_mock_event,
        call_multipart_mock_event_plain_text_json,
        call_multipart_mock_event_bad_request,
        call_post_nopayload,
        call_get_stream_response,
        call_post_fail_request,
        call_get_file_response,
        call_get_mock_auth_event,
        call_get_mock_auth_event_malformed_authorization,
        call_get_mock_auth_event_unauthorized,
        call_post_mock_auth_event,
        call_post_mock_auth_event_unauthorized,
        call_get_plugin_event_on_app,
        call_start_stream,
        call_stop_stream,
        call_start_service,
        call_stop_service,
    ]

    for test_func in test_list:
        logger.debug("=" * 120)
        logger.debug("Running web test %s...", test_func)
        await test_func(test_client)


@pytest.mark.order(2)
async def test_start_streams_on_startup(
    app_client,
):
    test_client = await app_client(streams=True)
    await call_stop_stream(test_client)
    await call_stop_service(test_client)
