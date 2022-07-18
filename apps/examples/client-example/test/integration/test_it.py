from dataclasses import dataclass
from typing import List, Type, Union
import pytest
from base64 import b64encode

from hopeit.app.context import EventContext
from hopeit.app.client import UnhandledResponse
from hopeit.dataobjects import EventPayload, dataobject
from hopeit.server.web import Unauthorized
from hopeit.testing.apps import execute_event, create_test_context

from model import Something, User, SomethingParams, SomethingNotFound
from client_example import CountAndSaveResult


@dataobject
@dataclass
class MockAuthInfo:
    access_token: str

    @staticmethod
    def mock_validate_token(token, context):
        app, user = token.split(',')
        return {
            'app': app, 'user': user
        }

    @staticmethod
    def mock_invalid_token(token, context):
        return None


async def custom_app_call(app_connection: str,
                          *, event: str, datatype: Type[str],
                          payload: EventPayload, context: EventContext,
                          **kwargs) -> Union[str, MockAuthInfo, SomethingNotFound, Something]:
    if app_connection == "simple_example_conn" and event == "save_something":
        assert payload == SomethingParams(id="id2", user="test-user")
        return "test_path"
    if app_connection == "simple_example_auth_conn" and event == "login":
        return MockAuthInfo(access_token="test-app,test-user")
    if app_connection == "simple_example_conn" and event == "query_something" and "item_id" in kwargs:
        if kwargs['item_id'] == "id_not_found":
            return SomethingNotFound('', kwargs['item_id'])
        return Something(kwargs['item_id'], User(id="test", name="test"))
    if app_connection == "simple_example_conn" and event == "query_something":
        raise UnhandledResponse("Missing 400 status handler, use `responses` to handle this exception",
                                "", 400)
    raise NotImplementedError("Test case not implemented in mock_app_call")


async def custom_app_call_list(app_connection: str,
                               *, event: str, datatype: Type[Something],
                               payload: EventPayload, context: EventContext,
                               **kwargs) -> List[Something]:
    if app_connection == "simple_example_conn" and event == "list_somethings":
        return [
            Something(id="test1", user=User(id="test", name="test")),
            Something(id="test2", user=User(id="test", name="test")),
        ]
    raise NotImplementedError("Test case not implemented in mock_app_call")


@pytest.mark.asyncio
async def test_query_item(monkeypatch, client_app_config):  # noqa: F811

    def mock_client_calls(module, context: EventContext):
        monkeypatch.setattr(module, "app_call", custom_app_call)
        monkeypatch.setattr(module, "app_call_list", custom_app_call_list)
        monkeypatch.setattr(module.auth, "validate_token", MockAuthInfo.mock_validate_token)

    context = create_test_context(
        client_app_config, "count_and_save",
        auth_info={'payload': b64encode(b'test-user:test-password').decode()}
    )

    result = await execute_event(
        app_config=client_app_config,
        event_name='count_and_save',
        payload=None,
        context=context,
        mocks=[mock_client_calls])

    assert result == CountAndSaveResult(count=2, save_path='test_path')


@pytest.mark.asyncio
async def test_login_response_not_recognized(monkeypatch, client_app_config):  # noqa: F811

    def mock_client_calls(module, context: EventContext):
        monkeypatch.setattr(module, "app_call", custom_app_call)
        monkeypatch.setattr(module, "app_call_list", custom_app_call_list)
        monkeypatch.setattr(module.auth, "validate_token", MockAuthInfo.mock_invalid_token)

    context = create_test_context(
        client_app_config, "count_and_save",
        auth_info={'payload': b64encode(b'test-user:test-password').decode()}
    )

    with pytest.raises(Unauthorized):
        await execute_event(
            app_config=client_app_config,
            event_name='count_and_save',
            payload=None,
            context=context,
            mocks=[mock_client_calls])


@pytest.mark.asyncio
async def test_handle_responses_something(monkeypatch, client_app_config):  # noqa: F811

    def mock_client_calls(module, context: EventContext):
        monkeypatch.setattr(module, "app_call", custom_app_call)        

    context = create_test_context(
        client_app_config, "handle_responses",
        auth_info={'payload': b64encode(b'test-user:test-password').decode()}
    )

    result = await execute_event(
        app_config=client_app_config,
        event_name='handle_responses',
        payload=None,
        context=context,
        mocks=[mock_client_calls],
        item_id="id_something",
        partition_key="YYYY/MM/DD/HH")

    assert result == "You get a 200 response with: 'Something(id='id_something', user=User(id='test'," \
        " name='test'), status=None, history=[])'"


@pytest.mark.asyncio
async def test_handle_responses_something_not_found(monkeypatch, client_app_config):  # noqa: F811

    def mock_client_calls(module, context: EventContext):
        monkeypatch.setattr(module, "app_call", custom_app_call)

    context = create_test_context(
        client_app_config, "handle_responses",
        auth_info={'payload': b64encode(b'test-user:test-password').decode()}
    )

    result = await execute_event(
        app_config=client_app_config,
        event_name='handle_responses',
        payload=None,
        context=context,
        mocks=[mock_client_calls],
        item_id="id_not_found",
        partition_key="YYYY/MM/DD/HH")

    assert result == "You get a 404 response with: 'SomethingNotFound(path='', id='id_not_found')'"
