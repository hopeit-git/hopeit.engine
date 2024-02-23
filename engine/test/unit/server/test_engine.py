import asyncio

import pytest  # type: ignore
from typing import Dict, Optional, List

from hopeit.app.context import EventContext, PostprocessHook
from hopeit.server.config import AuthType
from hopeit.server.events import EventHandler, get_event_settings
from hopeit.streams import StreamCircuitBreaker, StreamOSError

from hopeit.dataobjects import DataObject
from hopeit.app.config import AppConfig, StreamQueueStrategy
from hopeit.server.engine import AppEngine
from hopeit.testing.apps import service_running_mock
from mock_engine import MockEventHandler, MockStreamManager
from mock_app import MockData, MockResult  # type: ignore
from mock_app import mock_service_event
from mock_app import mock_app_config  # type: ignore  # noqa: F401
from mock_plugin import mock_plugin_config  # type: ignore  # noqa: F401


async def create_engine(app_config: AppConfig, plugin: AppConfig,
                        enabled_groups: Optional[List[str]] = None) -> AppEngine:
    if enabled_groups is None:
        enabled_groups = []
    engine = await AppEngine(app_config=app_config, plugins=[plugin], enabled_groups=enabled_groups).start()
    assert engine.stream_manager is not None
    return engine


async def create_plugin_engine(plugin: AppConfig, enabled_groups: Optional[List[str]] = None) -> AppEngine:
    if enabled_groups is None:
        enabled_groups = []
    engine = await AppEngine(app_config=plugin, plugins=[], enabled_groups=enabled_groups).start()
    assert engine.stream_manager is None
    return engine


async def invoke_execute(engine: AppEngine,
                         from_app: AppConfig,
                         event_name: str,
                         query_args: dict,
                         payload: DataObject,
                         expected: DataObject,
                         track_ids: Dict[str, str],
                         postprocess_expected: Optional[dict] = None):
    event_settings = get_event_settings(from_app.effective_settings, event_name)  # type: ignore
    context = EventContext(
        app_config=from_app,
        plugin_config=engine.app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=track_ids,
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    res = await engine.execute(
        context=context,
        query_args=query_args,
        payload=payload
    )
    assert res == expected
    if postprocess_expected:
        hook = PostprocessHook()
        await engine.postprocess(context=context, payload=res, response=hook)
        assert hook.headers == postprocess_expected['headers']
        assert hook.cookies == postprocess_expected['cookies']
        assert hook.status == postprocess_expected['status']


def setup_mocks(monkeypatch):
    monkeypatch.setattr(EventHandler, '__init__', MockEventHandler.__init__)
    monkeypatch.setattr(EventHandler, 'handle_async_event', MockEventHandler.handle_async_event)
    monkeypatch.setattr(EventHandler, 'postprocess', MockEventHandler.postprocess)


@pytest.mark.asyncio
async def test_execute(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_post_event',
                         query_args={"query_arg1": "ok"},
                         payload=payload,
                         expected=expected,
                         track_ids={
                            "track.request_id": "test_request_id",
                            "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
                            "track.session_id": "test_session_id"
                         })
    await engine.stop()


@pytest.mark.asyncio
async def test_execute_plugin(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    expected = "PluginEvent"
    expected_response = {
        'cookies': {'PluginCookie': ('PluginCookieValue', tuple(), {})},
        'headers': {'PluginHeader': 'PluginHeaderValue'},
        'status': 999
    }

    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', None)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    plugin_engine = await create_plugin_engine(plugin=mock_plugin_config)
    await invoke_execute(engine=plugin_engine, from_app=mock_plugin_config,
                         event_name='plugin_event',
                         query_args={},
                         payload=None,
                         expected=expected,
                         track_ids={
                            "track.request_id": "test_request_id",
                            "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
                            "track.session_id": "test_session_id"
                         },
                         postprocess_expected=expected_response)
    await plugin_engine.stop()


@pytest.mark.asyncio
async def test_execute_provided_request_id(
        monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    track_ids = {
        "track.request_id": "test_request_id",
        "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
        "track.session_id": "test_session_id"
    }
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'expected_track_ids', track_ids)

    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_post_event',
                         query_args={"query_arg1": "ok"},
                         payload=payload,
                         expected=expected,
                         track_ids=track_ids)
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    from mock_app import mock_event_dataobject_payload
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'call_function', mock_event_dataobject_payload.entry_point)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_dataobject_payload(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = """{"value": "ok"}"""
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_event_dataobject_payload', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_auto_queue(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write'
    assert engine.stream_manager.write_stream_queue == 'AUTO'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_propagate_queue(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', 'custom')
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.PROPAGATE
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.custom'
    assert engine.stream_manager.write_stream_queue == 'custom'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_drop_queue(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', 'custom')
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.DROP
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write'
    assert engine.stream_manager.write_stream_queue == 'AUTO'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_new_queue(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['custom']
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.custom'
    assert engine.stream_manager.write_stream_queue == 'custom'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_new_queue_propagate_auto(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['custom']
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.PROPAGATE
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.custom'
    assert engine.stream_manager.write_stream_queue == 'AUTO'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_new_queue_propagate(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', 'original')
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['custom']
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.PROPAGATE
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.custom'
    assert engine.stream_manager.write_stream_queue == 'original'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_new_queue_drop(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', 'original')
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['custom']
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.DROP
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.custom'
    assert engine.stream_manager.write_stream_queue == 'custom'
    assert engine.stream_manager.write_stream_payload == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_multiple_queues(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', 'original')
    mock_app_config.events['mock_read_write_stream'].read_stream.queues = \
        ['q1', 'q2']
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['q3', 'q4']
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.q4'
    assert engine.stream_manager.write_stream_queue == 'q4'
    assert engine.stream_manager.write_stream_payload == expected
    assert MockStreamManager.last_read_stream_names[-2:] == \
        ['mock_read_write_stream.read.q1', 'mock_read_write_stream.read.q2']
    assert MockStreamManager.last_read_queue_names[-2:] == \
        ['original', 'original']
    assert MockStreamManager.last_write_stream_names[-4:] == [
        'mock_read_write_stream.write.q3', 'mock_read_write_stream.write.q4',
        'mock_read_write_stream.write.q3', 'mock_read_write_stream.write.q4'
    ]
    assert MockStreamManager.last_write_queue_names[-4:] == \
        ['q3', 'q4', 'q3', 'q4']
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_multiple_queues_propagate(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', None)  # Will use last part of stream name
    mock_app_config.events['mock_read_write_stream'].read_stream.queues = \
        ['q1', 'q2']
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['q3', 'q4']
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.PROPAGATE
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.q4'
    assert engine.stream_manager.write_stream_queue == 'q2'
    assert engine.stream_manager.write_stream_payload == expected
    assert MockStreamManager.last_read_stream_names[-2:] == \
        ['mock_read_write_stream.read.q1', 'mock_read_write_stream.read.q2']
    assert MockStreamManager.last_read_queue_names[-2:] == \
        ['q1', 'q2']
    assert MockStreamManager.last_write_stream_names[-4:] == [
        'mock_read_write_stream.write.q3', 'mock_read_write_stream.write.q4',
        'mock_read_write_stream.write.q3', 'mock_read_write_stream.write.q4'
    ]
    assert MockStreamManager.last_write_queue_names[-4:] == \
        ['q1', 'q1', 'q2', 'q2']
    await engine.stop()


@pytest.mark.asyncio
async def test_read_write_stream_multiple_queues_propagate_AUTO(
    monkeypatch, mock_app_config, mock_plugin_config  # noqa: F811
):
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', {
        'track.operation_id': 'test_operation_id', 'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00', 'track.session_id': 'test_session_id',
        'stream.name': 'test_stream', 'stream.msg_id': '0000000000-0',
        'stream.consumer_group': 'test_group', 'event.app': 'mock_app.test'
    })
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'test_queue', 'custom')
    mock_app_config.events['mock_read_write_stream'].read_stream.queues = \
        ['q1', 'AUTO']
    mock_app_config.events['mock_read_write_stream'].write_stream.queues = \
        ['q3', 'AUTO']
    mock_app_config.events['mock_read_write_stream'].write_stream.queue_strategy = \
        StreamQueueStrategy.PROPAGATE
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_read_write_stream', test_mode=True)
    assert res == expected
    assert engine.stream_manager.write_stream_name == 'mock_read_write_stream.write.custom'
    assert engine.stream_manager.write_stream_queue == 'custom'
    assert engine.stream_manager.write_stream_payload == expected
    assert MockStreamManager.last_read_stream_names[-2:] == \
        ['mock_read_write_stream.read.q1', 'mock_read_write_stream.read']
    assert MockStreamManager.last_read_queue_names[-2:] == \
        ['custom', 'custom']
    assert MockStreamManager.last_write_stream_names[-4:] == [
        'mock_read_write_stream.write.q3', 'mock_read_write_stream.write.custom',
        'mock_read_write_stream.write.q3', 'mock_read_write_stream.write.custom'
    ]
    assert MockStreamManager.last_write_queue_names[-4:] == \
        ['custom', 'custom', 'custom', 'custom']
    await engine.stop()


@pytest.mark.asyncio
async def test_service_loop(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = "stream: service.0"
    expected = MockData("stream: service.0")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    monkeypatch.setattr(mock_service_event, 'service_running', service_running_mock)
    res = await engine.service_loop(event_name='mock_service_event', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_service_loop_timeout(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("timeout")
    expected = MockData("stream: service.1")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.service_loop(event_name='mock_service_timeout', test_mode=True)
    # Result could be TimeoutError ot CancelledError depending on execution environment
    assert isinstance(res, asyncio.TimeoutError) or isinstance(res, asyncio.CancelledError)
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_timeout_ok(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert res == expected
    await engine.stop()


async def test_read_stream_timeout_fail(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("timeout")
    expected = MockResult("none")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert isinstance(res, asyncio.TimeoutError) or isinstance(res, asyncio.CancelledError)
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_event_fail_and_process_next(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    setup_mocks(monkeypatch)

    payload = MockData("cancel")
    expected = MockResult("none")
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert isinstance(res, asyncio.CancelledError)

    payload = MockData("fail")
    expected = MockResult("none")
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert isinstance(res, ValueError)

    payload = MockData("ok")
    expected = MockResult("ok: ok")
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    res = await engine.read_stream(event_name='mock_stream_timeout', test_mode=True)
    assert res == expected

    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_stop_and_recover(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockStreamManager, 'error_pattern', [None, TypeError(), None, StreamOSError(), None])
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    stream_manager = StreamCircuitBreaker(
        stream_manager=MockStreamManager(address='test'),
        initial_backoff_seconds=0.1,
        max_backoff_seconds=0.2,
        num_failures_open_circuit_breaker=1,
    )
    monkeypatch.setattr(engine, 'stream_manager', stream_manager)

    # StreamOSError is produced
    res = await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    assert res is None  # Exit in test mode after 1 cycle before recovery

    # Force a second cycle
    res = await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    assert res == expected
    await engine.stop()


@pytest.mark.asyncio
async def test_read_stream_failed(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("fail")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', None)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    monkeypatch.setattr(engine, 'stream_manager', MockStreamManager(address='test'))
    try:
        await engine.read_stream(event_name='mock_stream_event', test_mode=True)
    except Exception as e:
        assert isinstance(e, ValueError)
    await engine.stop()


@pytest.mark.asyncio
async def test_write_stream(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData("ok")
    expected = MockResult("ok: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    stream_manager = MockStreamManager(address='test')
    monkeypatch.setattr(engine, 'stream_manager', stream_manager)
    event_info = mock_app_config.events['mock_write_stream_event']
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_write_stream_event',
                         query_args={},
                         payload=payload,
                         expected=expected,
                         track_ids={
                            "track.request_id": "test_request_id",
                            "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
                            "track.session_id": "test_session_id"
                         })
    assert stream_manager.write_stream_name == event_info.write_stream.name
    assert stream_manager.write_stream_payload == expected
    assert stream_manager.write_target_max_len == 10
    await engine.stop()


@pytest.mark.asyncio
async def test_write_stream_batch(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = "ok"
    expected = MockData("stream: ok.3")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    stream_manager = MockStreamManager(address='test')
    monkeypatch.setattr(engine, 'stream_manager', stream_manager)
    event_info = mock_app_config.events['mock_write_stream_event']
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_spawn_event',
                         query_args={},
                         payload=payload,
                         expected=expected,
                         track_ids={
                            "track.request_id": "test_request_id",
                            "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
                            "track.session_id": "test_session_id"
                         })
    assert stream_manager.write_stream_name == event_info.write_stream.name
    assert stream_manager.write_stream_payload == expected
    assert stream_manager.write_target_max_len == 10
    await engine.stop()


@pytest.mark.asyncio
async def test_execute_collector(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    payload = MockData(value="ok")
    expected = MockResult(value="step3: ok")
    setup_mocks(monkeypatch)
    monkeypatch.setattr(MockEventHandler, 'input_payload', payload)
    monkeypatch.setattr(MockEventHandler, 'expected_result', expected)
    monkeypatch.setattr(MockStreamManager, 'test_payload', expected)
    monkeypatch.setattr(MockEventHandler, 'test_track_ids', None)

    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config)
    await invoke_execute(engine=engine, from_app=engine.app_config,
                         event_name='mock_collector',
                         query_args={},
                         payload=payload,
                         expected=expected,
                         track_ids={
                            "track.request_id": "test_request_id",
                            "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
                            "track.session_id": "test_session_id"
                         })
    await engine.stop()


@pytest.mark.asyncio
async def test_start_all_groups(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    setup_mocks(monkeypatch)
    engine = await create_engine(app_config=mock_app_config, plugin=mock_plugin_config, enabled_groups=None)
    assert all(
        event_name in engine.effective_events
        for event_name in mock_app_config.events.keys()
    )


@pytest.mark.asyncio
async def test_start_single_group(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    setup_mocks(monkeypatch)
    engine = await create_engine(
        app_config=mock_app_config,
        plugin=mock_plugin_config,
        enabled_groups=['GROUP_A']
    )
    assert len(engine.effective_events) == 27
    assert all(
        event_name in engine.effective_events
        for event_name in ['mock_event', 'mock_post_event', 'mock_event_logging', 'mock_stream_event']
    )
    assert all(
        event_name in engine.effective_events
        for event_name, event_info in mock_app_config.events.items()
        if event_info.group in ('DEFAULT', 'GROUP_A')
    )


@pytest.mark.asyncio
async def test_start_multiple_groups(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    setup_mocks(monkeypatch)
    engine = await create_engine(
        app_config=mock_app_config,
        plugin=mock_plugin_config,
        enabled_groups=['GROUP_A', 'GROUP_B']
    )
    assert len(engine.effective_events) == 29
    assert all(
        event_name in engine.effective_events
        for event_name in [
            'mock_event', 'mock_post_event', 'mock_event_logging', 'mock_stream_event',
            'mock_stream_timeout', 'mock_multipart_event'
        ]
    )
    assert all(
        event_name in engine.effective_events
        for event_name, event_info in mock_app_config.events.items()
        if event_info.group in ('DEFAULT', 'GROUP_A', 'GROUP_B')
    )


@pytest.mark.asyncio
async def test_start_default_group(monkeypatch, mock_app_config, mock_plugin_config):  # noqa: F811
    setup_mocks(monkeypatch)
    engine = await create_engine(
        app_config=mock_app_config,
        plugin=mock_plugin_config,
        enabled_groups=['DEFAULT']
    )
    # Checking count it should be 21 events + 2 split events == 23
    assert len(engine.effective_events) == 23
    assert all(
        event_name not in engine.effective_events
        for event_name in ['mock_event', 'mock_post_event', 'mock_event_logging', 'mock_stream_event']
    )
    assert all(
        event_name in engine.effective_events
        for event_name, event_info in mock_app_config.events.items()
        if event_info.group == 'DEFAULT'
    )
