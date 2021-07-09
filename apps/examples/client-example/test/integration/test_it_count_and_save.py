from typing import List, Type, Union
import pytest
from base64 import b64encode

from hopeit.app.context import EventContext
from hopeit.dataobjects import EventPayload, EventPayloadType  # type: ignore
from hopeit.testing.apps import execute_event, create_test_context

from model import Something, User, SomethingParams
from client_example import CountAndSaveResult


async def custom_app_call(app_connection: str,
                        *, event: str, datatype: Type[EventPayloadType],
                        payload: EventPayload, context: EventContext,
                        **kwargs) -> Union[EventPayloadType, List[EventPayloadType]]:
    if app_connection == "simple_example_conn":
        if event == "list_somethings":
            return [
                Something(id="test1", user=User(id="test", name="test")),
                Something(id="test2", user=User(id="test", name="test")),
            ]
        elif event == "save_something":
            assert payload == SomethingParams(id=f"id2", user="test-user")
            return "test_path"

    raise NotImplementedError("Test case not implemented in mock_app_call")


@pytest.mark.asyncio
async def test_query_item(monkeypatch, client_app_config):  # noqa: F811
    
    def mock_client_calls(module, context: EventContext):
        monkeypatch.setattr(module, "app_call", custom_app_call)

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
