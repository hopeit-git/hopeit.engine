import json
import os
import uuid
import asyncio
import aiohttp

import aiojobs  # type: ignore
import pytest
from aiohttp import ClientResponse
from pytest_aiohttp import aiohttp_server, aiohttp_client  # type: ignore  # noqa: F401

import hopeit.server.web
from hopeit.server import api
from hopeit.server.web import start_server, stop_server, start_app
from hopeit.server.streams import StreamManager

from mock_engine import MockStreamManager, MockEventHandler
from mock_app import MockResult, mock_app_config  # type: ignore  # noqa: F401
from mock_plugin import mock_plugin_config  # type: ignore  # noqa: F401


async def call_get_mock_event(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'ok'},
        headers={'X-Track-Session-Id': 'test_session_id'}
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    assert res.headers.get('X-Status') == 'ok'
    result = (await res.read()).decode()
    assert result == '{"mock_event": "ok: ok"}'


async def call_get_mock_event_cors_allowed(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'ok'},
        headers={
            'X-Track-Session-Id': 'test_session_id',
            'Origin': 'http://test',
            'Host': 'test'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    assert res.headers.get('Access-Control-Allow-Origin') == 'http://test'
    assert res.headers.get('Access-Control-Allow-Credentials') == 'true'
    result = (await res.read()).decode()
    assert result == '{"mock_event": "ok: ok"}'


async def call_get_mock_event_cors_unknown(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'ok'},
        headers={
            'X-Track-Session-Id': 'test_session_id',
            'Origin': 'http://unknown',
            'Host': 'test'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    assert res.headers.get('Access-Control-Allow-Origin') is None
    assert res.headers.get('Access-Control-Allow-Credentials') is None
    assert res.cookies.get('Test-Cookie').value == 'ok'
    result = (await res.read()).decode()
    assert result == '{"mock_event": "ok: ok"}'


async def call_get_mock_event_special_case(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'no-ok'},
        headers={'x-track-session-id': 'test_session_id'}
    )
    assert res.status == 400
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    assert res.cookies.get('Test-Cookie').value == ''
    result = (await res.read()).decode()
    assert result == '{"mock_event": "not-ok: None"}'


async def call_get_fail_request(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'fail'},
        headers={
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 500
    result = (await res.read()).decode()
    assert result == '{"msg": "Test for error", "tb": ["AssertionError: Test for error\\n"]}'


async def call_post_mock_event(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'ok'},
        data='{"value": "ok"}',
        headers={
            'X-Track-Request-Id': 'test_request_id',
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id') == 'test_request_id'
    result = (await res.read()).decode()
    assert result == '{"value": "ok: ok", "processed": true}'


async def call_multipart_mock_event(client):
    os.makedirs('/tmp/call_multipart_mock_event/', exist_ok=True)
    with open('/tmp/call_multipart_mock_event/test_attachment', 'wb') as f:
        f.write(b'testdata')

    attachment = open('/tmp/call_multipart_mock_event/test_attachment', 'rb')
    with aiohttp.MultipartWriter("form-data", boundary=":") as mp:
        part = mp.append("value1")
        part.set_content_disposition('form-data', name="field1")
        part = mp.append("value2")
        part.set_content_disposition('form-data', name="field2")
        part = mp.append(attachment)
        part.set_content_disposition(
            'form-data', name="attachment", filename='secret.txt')

        res: ClientResponse = await client.post(
            '/api/mock-app/test/mock-multipart-event-test',
            params={'query_arg1': 'ok'},
            data=mp,
            headers={
                'X-Track-Request-Id': 'test_request_id',
                'X-Track-Session-Id': 'test_session_id',
                'Content-Type': 'multipart/form-data; boundary=":"'}
                )
        assert res.status == 200
        assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
        assert res.headers.get('X-Track-Request-Id') == 'test_request_id'
        result = (await res.read()).decode()
        assert result == '{"value": "field1=value1 field2=value2 attachment=secret.txt ok"}'


async def call_post_nopayload(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-post-nopayload',
        params={'query_arg1': 'ok'},
        headers={
            'X-Track-Request-Id': 'test_request_id',
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id') == 'test_request_id'
    result = (await res.read()).decode()
    assert result == '{"mock_post_nopayload": "ok: nopayload ok"}'


async def call_post_invalid_payload(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'ok'},
        data='{"value": invalid_json}',
        headers={
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 400
    result = (await res.read()).decode()
    assert result == \
        '{"msg": "Expecting value: line 1 column 11 (char 10)", "tb": ' \
        '["hopeit.app.errors.BadRequest: Expecting value: line 1 column 11 (char 10)\\n"]}'


async def call_post_fail_request(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-event-test',
        params={'query_arg1': 'fail'},
        data='{"value": "ok"}',
        headers={
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 500
    result = (await res.read()).decode()
    assert result == '{"msg": "Test for error", "tb": ["AssertionError: Test for error\\n"]}'


async def call_post_mock_collector(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-collector',
        params={},
        data='{"value": "ok"}',
        headers={
            'X-Track-Request-Id': 'test_request_id',
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id') == 'test_request_id'
    result = (await res.read()).decode()
    assert result == '{"value": ' \
        '"((ok+mock_collector+step1)&(ok+mock_collector+step2)+mock_collector+step3)", ' \
        '"processed": true}'


async def call_get_mock_spawn_event(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-spawn-event',
        params={'payload': 'ok'},
        data=None,
        headers={
            'X-Track-Request-Id': 'test_request_id',
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id') == 'test_request_id'
    result = (await res.read()).decode()
    assert result == '{"value": "stream: ok.2"}'


async def call_get_mock_timeout_ok(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-timeout',
        params={'delay': 1},
        data=None,
        headers={
            'X-Track-Request-Id': 'test_request_id',
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id') == 'test_request_id'
    result = (await res.read()).decode()
    assert result == '{"mock_timeout": "ok"}'


async def call_get_mock_timeout_exceeded(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-timeout',
        params={'delay': 5},
        data=None,
        headers={
            'X-Track-Request-Id': 'test_request_id',
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 500
    result = (await res.read()).decode()
    assert result == '{"msg": "Response timeout exceeded seconds=2.0", '\
                     '"tb": ["TimeoutError: Response timeout exceeded seconds=2.0\\n"]}'


async def call_get_file_response(client):
    file_name = str(uuid.uuid4()) + '.txt'
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-file-response',
        params={'file_name': file_name},
        headers={'X-Track-Session-Id': 'test_session_id'}
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    assert res.headers.get("Content-Disposition") == f"attachment; filename={file_name}"
    assert res.headers.get("Content-Type") == 'text/plain'
    result = (await res.read()).decode()
    assert result == 'mock_file_response test file_response'


async def call_get_mock_auth_event(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-auth',
        headers={
            'X-Track-Session-Id': 'test_session_id',
            'Authorization': 'Basic 1234567890=='
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    result = (await res.read()).decode()
    assert result == '{"mock_auth": "ok"}'


async def call_get_mock_auth_event_malformed_authorization(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-auth',
        headers={
            'X-Track-Session-Id': 'test_session_id',
            'Authorization': 'BAD_AUTHORIZATION'
        }
    )
    assert res.status == 400
    result = (await res.read()).decode()
    assert json.loads(result) == {
        "msg": "Malformed Authorization",
        "tb": ["hopeit.app.errors.BadRequest: Malformed Authorization\n"]
    }


async def call_get_mock_auth_event_unauthorized(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-auth',
        headers={
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 401
    result = (await res.read()).decode()
    assert result == '{"msg": "Unsecured", "tb": ["hopeit.app.errors.Unauthorized: Unsecured\\n"]}'


async def call_post_mock_auth_event(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-post-auth',
        data='{"value": "test_data"}',
        headers={
            'X-Track-Session-Id': 'test_session_id',
            'Authorization': 'Basic 1234567890=='
        }
    )
    assert res.status == 200
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    result = (await res.read()).decode()
    assert result == '{"mock_post_auth": "ok: test_data"}'


async def call_post_mock_auth_event_unauthorized(client):
    res: ClientResponse = await client.post(
        '/api/mock-app/test/mock-post-auth',
        data='{"value": "test_data"}',
        headers={
            'X-Track-Session-Id': 'test_session_id'
        }
    )
    assert res.status == 401
    result = (await res.read()).decode()
    assert result == '{"msg": "Unsecured", "tb": ["hopeit.app.errors.Unauthorized: Unsecured\\n"]}'


async def call_get_plugin_event_on_app(client):
    res: ClientResponse = await client.get(
        '/api/mock-app/test/mock-plugin/test/plugin-event',
        headers={'X-Track-Session-Id': 'test_session_id'}
    )
    assert res.status == 999
    assert res.headers.get('X-Track-Session-Id') == 'test_session_id'
    assert res.headers.get('X-Track-Request-Id')
    assert res.headers.get('X-Track-Request-Ts')
    assert res.headers.get('PluginHeader') == 'PluginHeaderValue'
    assert res.cookies.get('PluginCookie').value == "PluginCookieValue"
    result = (await res.read()).decode()
    assert result == '{"plugin_event": "PluginEvent.postprocess"}'


async def call_start_stream(client):
    res = await client.get(
        '/mgmt/mock-app/test/mock-stream-event/start'
    )
    assert res.status == 200


async def call_start_service(client):
    res = await client.get(
        '/mgmt/mock-app/test/mock-service-event/start'
    )
    assert res.status == 200


async def call_stop_stream(client):
    res = await client.get(
        '/mgmt/mock-app/test/mock-stream-event/stop'
    )
    assert res.status == 200


async def call_stop_service(client):
    res = await client.get(
        '/mgmt/mock-app/test/mock-service-event/stop'
    )
    assert res.status == 200


async def start_test_server(
        mock_app_config, mock_plugin_config, aiohttp_server, streams=None):  # noqa: F811
    scheduler = await aiojobs.create_scheduler()
    await start_server(mock_app_config.server)
    await start_app(mock_plugin_config, scheduler)
    await start_app(mock_app_config, scheduler, start_streams=streams)
    test_server = await aiohttp_server(hopeit.server.web.web_server)
    print('Test engine started:', test_server)
    return test_server


def _setup(monkeypatch,
           loop,
           mock_app_config,  # noqa: F811
           mock_plugin_config,  # noqa: F811
           aiohttp_server,  # noqa: F811
           aiohttp_client,  # noqa: F811
           streams=None):
    stream_event = MockResult("ok: ok")
    monkeypatch.setattr(StreamManager, '__init__', MockStreamManager.__init__)
    monkeypatch.setattr(StreamManager, 'connect', MockStreamManager.connect)
    monkeypatch.setattr(StreamManager,
                        'ensure_consumer_group', MockStreamManager.ensure_consumer_group)
    monkeypatch.setattr(StreamManager, 'write_stream', MockStreamManager.write_stream)
    monkeypatch.setattr(StreamManager, 'read_stream', MockStreamManager.read_stream)
    monkeypatch.setattr(StreamManager, 'ack_read_stream', MockStreamManager.ack_read_stream)
    monkeypatch.setattr(StreamManager, 'close', MockStreamManager.close)
    monkeypatch.setattr(MockStreamManager, 'test_payload', stream_event)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    api.clear()
    loop.run_until_complete(start_test_server(
        mock_app_config, mock_plugin_config, aiohttp_server, streams))
    return loop.run_until_complete(aiohttp_client(hopeit.server.web.web_server))


@pytest.fixture
def loop():
    """Ensure usable event loop for everyone.

    If you comment this fixture out, default pytest-aiohttp one is used
    and things start failing (when redis pool is in place).
    """
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        return asyncio.new_event_loop()


@pytest.mark.order1
def test_all(monkeypatch,
             loop,
             mock_app_config,  # noqa: F811
             mock_plugin_config,  # noqa: F811
             aiohttp_server,  # noqa: F811
             aiohttp_client):  # noqa: F811
    test_client = _setup(monkeypatch, loop, mock_app_config, mock_plugin_config,
                         aiohttp_server, aiohttp_client)

    # loop.run_until_complete(call_get_mock_event(test_client))
    # loop.run_until_complete(call_get_mock_event_cors_allowed(test_client))
    # loop.run_until_complete(call_get_mock_event_cors_unknown(test_client))
    # loop.run_until_complete(call_get_mock_event_special_case(test_client))
    # loop.run_until_complete(call_post_invalid_payload(test_client))
    # loop.run_until_complete(call_post_mock_collector(test_client))
    # loop.run_until_complete(call_get_mock_timeout_ok(test_client))
    # loop.run_until_complete(call_get_mock_timeout_exceeded(test_client))
    # loop.run_until_complete(call_get_fail_request(test_client))
    # loop.run_until_complete(call_get_mock_spawn_event(test_client))
    # loop.run_until_complete(call_post_mock_event(test_client))
    loop.run_until_complete(call_multipart_mock_event(test_client))
    # loop.run_until_complete(call_post_nopayload(test_client))
    # loop.run_until_complete(call_post_fail_request(test_client))
    # loop.run_until_complete(call_get_file_response(test_client))
    # loop.run_until_complete(call_get_mock_auth_event(test_client))
    # loop.run_until_complete(call_get_mock_auth_event_malformed_authorization(test_client))
    # loop.run_until_complete(call_get_mock_auth_event_unauthorized(test_client))
    # loop.run_until_complete(call_post_mock_auth_event(test_client))
    # loop.run_until_complete(call_post_mock_auth_event_unauthorized(test_client))
    # loop.run_until_complete(call_get_plugin_event_on_app(test_client))
    # loop.run_until_complete(call_start_stream(test_client))
    # loop.run_until_complete(call_stop_stream(test_client))
    # loop.run_until_complete(call_start_service(test_client))
    # loop.run_until_complete(call_stop_service(test_client))

    # loop.run_until_complete(stop_server())


# @pytest.mark.order2
# def test_start_streams(monkeypatch,
#                        loop,
#                        mock_app_config,  # noqa: F811
#                        mock_plugin_config,  # noqa: F811
#                        aiohttp_server,  # noqa: F811
#                        aiohttp_client):  # noqa: F811
#     test_client = _setup(monkeypatch, loop, mock_app_config, mock_plugin_config,
#                          aiohttp_server, aiohttp_client, streams=True)
#     loop.run_until_complete(call_stop_stream(test_client))
#     loop.run_until_complete(stop_server())
