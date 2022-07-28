import asyncio

import pytest

import hopeit.apps_client as apps_client_module
from hopeit.apps_client import AppsClientException, ClientLoadBalancerException
from hopeit.app.client import AppConnectionNotFound, app_call, app_call_list, app_client, UnhandledResponse
from hopeit.app.config import AppConfig
from hopeit.app.errors import Unauthorized
from hopeit.server.config import AuthType
from hopeit.testing.apps import create_test_context

from . import MockClientSession, MockPayloadData, MockResponseData, \
    init_mock_client_app, init_mock_client_app_plugin


@pytest.mark.asyncio
async def test_client_get(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=MockResponseData, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == MockResponseData(
            value="ok", param="test_param_value",
            host="http://test-host1",
            log={"http://test-host1": 1}
        )


@pytest.mark.asyncio
async def test_client_app_plugin(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app_plugin(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config,
            "test-plugin", "test-event-plugin", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        context.auth_info = {
            "auth_type": AuthType.BASIC,
            "payload": "user:pass"
        }
        result = await app_call(
            "test_app_plugin_connection", event="test_event_plugin",
            datatype=MockResponseData, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == MockResponseData(
            value="ok", param="test_param_value",
            host="http://test-host1",
            log={"http://test-host1": 1}
        )


@pytest.mark.asyncio
async def test_client_post(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-post", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        result = await app_call_list(
            "test_app_connection", event="test_event_post",
            datatype=MockResponseData,
            payload=MockPayloadData("payload"), context=context,
            test_param="test_param_value"
        )
        assert result == [MockResponseData(
            value="payload ok", param="test_param_value",
            host="http://test-host1",
            log={"http://test-host1": 1}
        )]


@pytest.mark.asyncio
async def test_client_connection_not_found(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        with pytest.raises(AppConnectionNotFound):
            await app_call(
                "test_app_connection", event="invalid_event",
                datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )


@pytest.mark.asyncio
async def test_load_balancer_next_host(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=MockResponseData, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == MockResponseData(
            value="ok", param="test_param_value", host="http://test-host1",
            log={"http://test-host1": 1}
        )

        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=MockResponseData, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 1, "http://test-host2": 1}
        )

        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=MockResponseData, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == MockResponseData(
            value="ok", param="test_param_value", host="http://test-host1",
            log={"http://test-host1": 2, "http://test-host2": 1}
        )


@pytest.mark.asyncio
async def test_load_balancer_retry(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=1
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        MockClientSession.set_failure("http://test-host1", 500)
        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=MockResponseData, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 1, "http://test-host2": 1}
        )


@pytest.mark.asyncio
async def test_load_balancer_retry_and_fail(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=1
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        MockClientSession.set_failure("http://test-host1", 500)
        MockClientSession.set_failure("http://test-host2", 500)

        with pytest.raises(AppsClientException):
            await app_call(
                "test_app_connection", event="test_event_get",
                datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
            assert MockClientSession.call_log == {"http://test-host1": 1, "http://test-host2": 1}


@pytest.mark.asyncio
async def test_load_balancer_disable_retry(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=0
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        MockClientSession.set_failure("http://test-host1", 500)

        with pytest.raises(AppsClientException):
            await app_call(
                "test_app_connection", event="test_event_get",
                datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
            assert MockClientSession.call_log == {"http://test-host1": 1}


@pytest.mark.asyncio
async def test_load_balancer_unauthorized(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=0
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        MockClientSession.set_failure("http://test-host1", 401)

        with pytest.raises(Unauthorized):
            await app_call(
                "test_app_connection", event="test_event_get",
                datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
            assert MockClientSession.call_log == {"http://test-host1": 1}


def set_settings(app_config: AppConfig, **kwargs):
    app_config.settings['test_app_connection'].update(kwargs)


@pytest.mark.asyncio
async def test_load_balancer_cb_open(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=1,
            circuit_breaker_open_failures=10,
            circuit_breaker_failure_reset_seconds=60,
            circuit_breaker_open_seconds=60
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        client = app_client("test_app_connection", context)

        MockClientSession.set_failure("http://test-host1", 500)

        for _ in range(20):
            result = await client.call(
                "test_event_get", datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
        assert result == [MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 10, "http://test-host2": 20}
        )]


@pytest.mark.asyncio
async def test_load_balancer_no_hosts_available(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=1,
            circuit_breaker_open_failures=10,
            circuit_breaker_failure_reset_seconds=60,
            circuit_breaker_open_seconds=60
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        MockClientSession.set_failure("http://test-host1", 500)
        MockClientSession.set_failure("http://test-host2", 500)

        client = app_client("test_app_connection", context)

        for _ in range(10):
            try:
                await client.call(
                    "test_event_get", datatype=MockResponseData, payload=None, context=context,
                    test_param="test_param_value"
                )
            except:  # noqa: E722
                pass  # Opening circuit breakers

        assert MockClientSession.call_log == {"http://test-host1": 10, "http://test-host2": 10}
        with pytest.raises(ClientLoadBalancerException):
            await client.call(
                "test_event_get", datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
            assert MockClientSession.call_log == {"http://test-host1": 10, "http://test-host2": 10}


@pytest.mark.asyncio
async def test_load_balancer_cb_recover(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        set_settings(
            mock_client_app_config,
            retries=1,
            circuit_breaker_open_failures=10,
            circuit_breaker_failure_reset_seconds=5,
            circuit_breaker_open_seconds=2
        )
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        client = app_client("test_app_connection", context)

        MockClientSession.set_failure("http://test-host1", 500)

        for _ in range(20):
            result = await client.call(
                "test_event_get", datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
        assert result == [MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 10, "http://test-host2": 20}
        )]

        await asyncio.sleep(3)

        for _ in range(20):
            result = await client.call(
                "test_event_get", datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
        assert result == [MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 11, "http://test-host2": 40}
        )]

        await asyncio.sleep(6)

        for _ in range(20):
            result = await client.call(
                "test_event_get", datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
        assert result == [MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 21, "http://test-host2": 60}
        )]

        MockClientSession.set_failure("http://test-host1", 0)

        await asyncio.sleep(3)

        for _ in range(20):
            result = await client.call(
                "test_event_get", datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value"
            )
        assert result == [MockResponseData(
            value="ok", param="test_param_value", host="http://test-host2",
            log={"http://test-host1": 31, "http://test-host2": 70}
        )]


@pytest.mark.asyncio
async def test_client_session_lifecycle(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        assert MockClientSession.session_open
        context = create_test_context(mock_client_app_config, "mock_client_event")
        client = app_client("test_app_connection", context)
        await client.stop()
        assert MockClientSession.session_open is False


@pytest.mark.asyncio
async def test_client_responses(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        MockClientSession.set_alternate_response("http://test-host1", 403)

        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=MockResponseData, payload=None, context=context,
            responses={403: MockResponseData}, test_param="test_param_value"
        )
        assert result == MockResponseData(value="ok", param="test_param_value", host="http://test-host1",
                                          log={"http://test-host1": 1})


@pytest.mark.asyncio
async def test_client_get_str(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")

        MockClientSession.set_alternate_response("http://test-host1", 200, 'text/plain')

        result = await app_call(
            "test_app_connection", event="test_event_get",
            datatype=str, payload=None, context=context,
            test_param="test_param_value"
        )
        assert result == "MockResponseData(value='ok', param='test_param_value'," \
                         " host='http://test-host1', log={'http://test-host1': 1})"


@pytest.mark.asyncio
async def test_client_list_responses(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-post", "ok"
        )

        MockClientSession.set_alternate_response("http://test-host1", 403)

        context = create_test_context(mock_client_app_config, "mock_client_event")
        result = await app_call_list(
            "test_app_connection", event="test_event_post",
            datatype=MockResponseData,
            payload=MockPayloadData("payload"), context=context,
            responses={403: MockResponseData},
            test_param="test_param_value"
        )
        assert result == [MockResponseData(
            value="payload ok", param="test_param_value",
            host="http://test-host1",
            log={"http://test-host1": 1}
        )]


async def test_client_unhandled_response_type_error(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        MockClientSession.set_alternate_response("http://test-host1", 405)
        with pytest.raises(UnhandledResponse) as unhandled_response:
            await app_call(
                "test_app_connection", event="test_event_get",
                datatype=MockResponseData, payload=None, context=context,
                test_param="test_param_value")
        assert str(unhandled_response.value) == 'Missing 405 status handler, use `responses` to handle this exception'
        assert unhandled_response.value.status == 405
        assert unhandled_response.value.response == "MockResponseData(value='ok', param='test_param_value'," \
                                                    " host='http://test-host1', log={'http://test-host1': 1})"


async def test_client_unhandled_response_key_error(monkeypatch, mock_client_app_config, mock_auth):
    async with MockClientSession.lock:
        await init_mock_client_app(
            apps_client_module, monkeypatch, mock_auth, mock_client_app_config, "test-event-get", "ok"
        )
        context = create_test_context(mock_client_app_config, "mock_client_event")
        MockClientSession.set_alternate_response("http://test-host1", 405)
        with pytest.raises(UnhandledResponse) as unhandled_response:
            await app_call(
                "test_app_connection", event="test_event_get",
                datatype=MockResponseData, payload=None, context=context,
                responses={403: MockResponseData},
                test_param="test_param_value"
            )
        assert str(unhandled_response.value) == 'Missing 405 status handler, use `responses` to handle this exception'
        assert unhandled_response.value.status == 405
        assert unhandled_response.value.response == "MockResponseData(value='ok', param='test_param_value'," \
                                                    " host='http://test-host1', log={'http://test-host1': 1})"
