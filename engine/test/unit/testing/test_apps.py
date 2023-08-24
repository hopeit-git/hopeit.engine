import uuid
import os
import importlib
from pathlib import Path
from types import ModuleType

import pytest  # type: ignore

from hopeit.app.context import EventContext, PostprocessHook, PreprocessHeaders, PreprocessHook
from hopeit.server.config import AuthType
from hopeit.testing.apps import config, server_config, create_test_context, execute_event, execute_service, TestingException
from mock_app import mock_app_config, MockData, mock_event, MockResult  # noqa: F401


def test_config(mock_app_config):  # noqa: F811
    file_name = Path('/tmp') / (str(uuid.uuid4()) + '.json')
    expected = mock_app_config
    with open(file_name, 'w') as f:
        f.write(expected.to_json())
    result = config(file_name)
    os.remove(file_name)
    assert result.app == expected.app
    assert result.engine == expected.engine
    assert result.events == expected.events
    assert result.server == server_config()


def test_create_test_context(mock_app_config):  # noqa: F811
    result = create_test_context(mock_app_config, 'mock_event')
    assert isinstance(result, EventContext)
    assert result.app == mock_app_config.app
    assert result.event_name == 'mock_event'
    assert result.track_ids == {
            'track.operation_id': 'test_operation_id',
            'track.request_id': 'test_request_id',
            'track.request_ts': result.track_ids['track.request_ts'],
            'track.session_id': '',
            'event.app': 'mock_app.test'
    }
    assert result.auth_info == {'auth_type': AuthType.UNSECURED, 'allowed': 'true'}


@pytest.mark.asyncio
async def test_execute_event(mock_app_config):  # noqa: F811
    result = await execute_event(mock_app_config, 'mock_event', None, query_arg1='ok')
    assert result == 'ok: ok'


@pytest.mark.asyncio
async def test_execute_event_and_postprocess(mock_app_config):  # noqa: F811
    result, pp_result, response = await execute_event(
        mock_app_config, 'mock_event', None, query_arg1='ok', postprocess=True)
    assert result == 'ok: ok'
    assert pp_result == 'ok: ok'
    assert response.status == 200
    assert response.headers == {'X-Status': 'ok'}
    assert response.cookies == {'Test-Cookie': ('ok', tuple(), {})}


@pytest.mark.asyncio
async def test_execute_event_failed_case(mock_app_config):  # noqa: F811
    with pytest.raises(AssertionError):
        await execute_event(mock_app_config, 'mock_event', None, query_arg1='fail', postprocess=True)


@pytest.mark.asyncio
async def test_execute_event_special_case(mock_app_config):  # noqa: F811
    result, pp_result, response = await execute_event(
        mock_app_config, 'mock_event', None, query_arg1='no-ok', postprocess=True)
    assert result == 'None'
    assert pp_result == 'not-ok: None'
    assert response.status == 400


@pytest.mark.asyncio
async def test_execute_spawn_event(mock_app_config):  # noqa: F811
    result = await execute_event(mock_app_config, 'mock_spawn_event', 'ok')
    assert result == [MockData(value='stream: ok.0'),
                      MockData(value='stream: ok.1'),
                      MockData(value='stream: ok.2')]


@pytest.mark.asyncio
async def test_execute_service(mock_app_config):  # noqa: F811
    result = await execute_service(mock_app_config, 'mock_service_event', max_events=3)
    assert result == [MockData(value='stream: service.0'),
                      MockData(value='stream: service.1'),
                      MockData(value='stream: service.2')]

@pytest.mark.asyncio
async def test_execute_service_unhappy(mock_app_config):  # noqa: F811
    with pytest.raises(TestingException):
        await execute_service(mock_app_config, 'mock_service_event_unhappy', max_events=3)


@pytest.mark.asyncio
async def test_execute_shuffle_event(mock_app_config):  # noqa: F811
    result = await execute_event(mock_app_config, 'mock_shuffle_event', 'ok')
    assert result == [MockResult(value='ok: ok.0', processed=True),
                      MockResult(value='ok: ok.1', processed=True),
                      MockResult(value='ok: ok.2', processed=True)]


@pytest.mark.asyncio
async def test_execute_shuffle_event_default_step(mock_app_config):  # noqa: F811
    result = await execute_event(mock_app_config, 'mock_shuffle_event', 'none')
    assert result == [MockResult(value='default', processed=True),
                      MockResult(value='default', processed=True),
                      MockResult(value='default', processed=True)]


@pytest.mark.asyncio
async def test_execute_parallelize_event(mock_app_config):  # noqa: F811
    result, pp_result, response = \
        await execute_event(mock_app_config, 'mock_parallelize_event', payload='part-a.part-b', postprocess=True)
    assert result == ['a: part-a', 'b: part-b']
    assert pp_result == 'Events submitted.'


@pytest.mark.asyncio
async def test_execute_parallelize_event_no_shuffle(mock_app_config):  # noqa: F811
    def mock_steps(module, context):
        setattr(module, '__steps__', ['produce_messages', 'process_a', 'process_b'])

    result = await execute_event(
        mock_app_config, 'mock_parallelize_event', payload='part-a.part-b', mocks=[mock_steps])
    assert result == ['a: part-a', 'b: part-b']


@pytest.mark.asyncio
async def test_execute_shuffle_event_default_step_fail(mock_app_config):  # noqa: F811
    with pytest.raises(AssertionError):
        await execute_event(mock_app_config, 'mock_shuffle_event', 'fail')


def mock_module(module: ModuleType, context: EventContext):
    async def mock_handle_ok_case(payload: MockData, context: EventContext) -> str:
        return "mock: " + payload.value
    setattr(module, "handle_ok_case", mock_handle_ok_case)


@pytest.mark.asyncio
async def test_execute_event_with_mocks(mock_app_config):  # noqa: F811
    result = await execute_event(mock_app_config, 'mock_event', None, mocks=[mock_module], query_arg1='ok')
    assert result == 'mock: ok'
    importlib.reload(mock_event)


@pytest.mark.asyncio
async def test_execute_multipart_event(mock_app_config):  # noqa: F811

    fields = {
        'field1': 'value1',
        'field2': {'value': 'value2'},
        'attachment': 'test_file_name.bytes'
    }

    upload = {
        'attachment': b'testdata'
    }

    result = await execute_event(
        mock_app_config, 'mock_multipart_event', None,
        fields=fields, upload=upload,
        query_arg1='ok', preprocess=True
    )
    assert result == MockData(value='field1=value1 field2=value2 attachment=test_file_name.bytes ok')


@pytest.mark.asyncio
async def test_execute_event_preprocess(mock_app_config):  # noqa: F811

    def mock_hooks(module, context: EventContext, preprocess_hook: PreprocessHook, postprocess_hook: PostprocessHook):
        preprocess_hook.headers = PreprocessHeaders.from_dict({'X-Track-Request-Id': 'Testing!'})
        assert postprocess_hook.headers.get('recognized') is None

    result, pp_result, response = await execute_event(
        mock_app_config, 'mock_post_preprocess', MockData(value='ok'),
        query_arg1='ok', preprocess=True, postprocess=True,
        mocks=[mock_hooks]
    )
    assert result == MockData(value='ok: Testing!')
    assert pp_result == result
    assert response.headers['recognized'] == 'ok: Testing!'


@pytest.mark.asyncio
async def test_execute_event_preprocess_no_datatype(mock_app_config):  # noqa: F811

    def mock_hooks(module, context: EventContext, preprocess_hook: PreprocessHook, postprocess_hook: PostprocessHook):
        preprocess_hook.headers = PreprocessHeaders.from_dict({'X-Track-Request-Id': 'Testing!'})
        preprocess_hook.payload_raw = b'OK\n'
        assert postprocess_hook.headers.get('recognized') is None

    result, pp_result, response = await execute_event(
        mock_app_config, 'mock_post_preprocess_no_datatype',
        payload=None, query_arg1='ok', preprocess=True, postprocess=True,
        mocks=[mock_hooks]
    )
    assert result == MockData(value='ok: Testing!')
    assert pp_result == result
    assert response.headers['recognized'] == 'ok: Testing!'
