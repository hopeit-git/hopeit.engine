"""
Test utilities/wrappers for app development
"""
from pathlib import Path
from types import ModuleType
from typing import Union, Callable, List, Optional, Dict, Tuple, Any
from datetime import datetime, timezone

from hopeit.app.config import AppConfig, parse_app_config_json, EventDescriptor
from hopeit.app.context import EventContext, PostprocessHook, PreprocessHook
from hopeit.dataobjects import DataObject, EventPayload
from hopeit.dataobjects.payload import Payload
from hopeit.server.config import AuthType, ServerConfig, LoggingConfig
from hopeit.server.events import EventHandler, get_event_settings
from hopeit.server.steps import split_event_stages, find_datatype_handler
from hopeit.server.imports import find_event_handler
from hopeit.server.logger import engine_logger
from hopeit.testing.hooks import MockFileHook, MockMultipartReader
from multidict import CIMultiDict, CIMultiDictProxy

__all__ = [
    'config',
    'server_config',
    'create_test_context',
    'execute_event'
]

logger = engine_logger()


def config(path: Union[str, Path]) -> AppConfig:
    if isinstance(path, str):
        path = Path(path)
    with open(path, 'r', encoding="utf-8") as f:
        app_config = parse_app_config_json(f.read())
        app_config.server = server_config()
        return app_config


def server_config():
    return ServerConfig(
        logging=LoggingConfig(log_level='DEBUG', log_path='logs/')
    )


def create_test_context(app_config: AppConfig, event_name: str,
                        track_ids: Optional[dict] = None,
                        auth_info: Optional[dict] = None) -> EventContext:
    """
    Creates an EventContext object to be used in tests

    :param app_config: AppConfig, app confioguration
    :param event_name: str, event_name to be called
    :param track_ids: dict, optional: addictional key/values to add to track_ids section. By default
        required track_ids will be generated with default test or empty values.
    :param auth_info: dict, optional: additional auth_info to inject. By default Unsecured auth_info
        will be generated.
    """
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name=event_name,
        settings=get_event_settings(app_config.effective_settings, event_name),  # type: ignore
        track_ids={
            **{
                k: '' for k in app_config.engine.track_headers
            },
            'track.operation_id': 'test_operation_id',
            'track.request_id': 'test_request_id',
            'track.request_ts': datetime.now(tz=timezone.utc).isoformat(),
            **({} if track_ids is None else track_ids)
        },
        auth_info={
            'auth_type': AuthType.UNSECURED, 'allowed': 'true',
            **({} if auth_info is None else auth_info)
        }
    )


def _apply_mocks(context: EventContext,
                 handler: EventHandler,
                 event_name: str,
                 effective_events: Dict[str, EventDescriptor],
                 preprocess_hook: Optional[PreprocessHook],
                 postprocess_hook: Optional[PostprocessHook],
                 mocks: List[Callable[[ModuleType, EventContext], None]]):
    """
    Execute a list of functions to mock module properties.
    """
    module, _, _ = handler.modules[event_name]
    logger.debug(context, f"[test.apps] executing mocks for module={module.__name__}...")
    for mock in mocks:
        hooks: Dict[str, Any] = {}
        if preprocess_hook is not None:
            hooks['preprocess_hook'] = preprocess_hook
        if postprocess_hook is not None:
            hooks['postprocess_hook'] = postprocess_hook
        mock(module, context, **hooks)  # type: ignore
    handler.load_modules(effective_events=effective_events)
    logger.debug(context, '[test.apps] mocking done.')


async def execute_event(app_config: AppConfig,
                        event_name: str,
                        payload: Optional[EventPayload],
                        mocks: Optional[List[Callable[[ModuleType, EventContext], None]]] = None,
                        *,
                        fields: Optional[Dict[str, str]] = None,
                        upload: Optional[Dict[str, bytes]] = None,
                        preprocess: bool = False,
                        postprocess: bool = False,
                        context: Optional[EventContext] = None,
                        **kwargs) -> Union[
                            Optional[EventPayload],
                            List[EventPayload],
                            Tuple[Optional[EventPayload], EventPayload, PostprocessHook],
                            Tuple[List[EventPayload], EventPayload, PostprocessHook]]:
    """
    Test executes an app event.

    Notice that event implementation file needs to be saved to disk since this will simulate
    execution similar to how engine actually execute events. Writing to stream will be ignored.

    :param app_config: AppConfig, load using `app_config = config('path/to/app-config.json')`
    :param event_name: str, name of the event / module to execute
    :param payload: test payload to send to initial step
    :param mocks: lists of functions to execute in order to mock functionality
    :param postprocess: enables testing __postprocess__ called with last step result or
        result before a SHUFFLE step if present.
    :param context: EventContext, optional EventContext to use when calling event. If not provided
        a default context will be created.
    :param kwargs: that will be forwarded to the initial step of the event
    :return: the results of executing the event, for simple events it will be a single object,
        for events with initial Spawn[...] the results will be collected as a list.
        If postprocess is true, a tuple of 3 elements is return, first element is results as described
        above, second element the output of call to __postprocess__, and third one a PostprocessHook
        with response information used during call to __postprocess__
    """
    async def _postprocess(hook: PostprocessHook, results: List[EventPayload]) -> EventPayload:
        assert context is not None
        pp_payload = results[-1] if len(results) > 0 else None
        return await handler.postprocess(context=context, payload=pp_payload, response=hook)

    async def _preprocess(hook: PreprocessHook, payload: EventPayload) -> EventPayload:
        assert context is not None
        return await handler.preprocess(
            context=context, query_args=kwargs, payload=payload, request=hook)

    if context is None:
        context = create_test_context(app_config, event_name)

    event_info = app_config.events[event_name]
    impl = find_event_handler(app_config=app_config, event_name=event_name, event_info=event_info)
    effective_events = {**split_event_stages(app_config.app, event_name, event_info, impl)}
    handler = EventHandler(
        app_config=app_config, plugins=[],
        effective_events=effective_events,
        settings=app_config.effective_settings  # type: ignore
    )

    preprocess_hook, postprocess_hook = None, None
    if preprocess:
        preprocess_hook = PreprocessHook(
            headers=CIMultiDictProxy(CIMultiDict()),
            multipart_reader=MockMultipartReader(fields or {}, upload or {}),  # type: ignore
            file_hook_factory=MockFileHook,
            payload_raw=b'' if payload is None else Payload.to_json(payload).encode()
        )
    if postprocess:
        postprocess_hook = PostprocessHook()
    if mocks is not None:
        _apply_mocks(context, handler, event_name, effective_events, preprocess_hook, postprocess_hook, mocks)

    datatype = find_datatype_handler(app_config=app_config, event_name=event_name, event_info=event_info)
    if preprocess_hook:
        payload = await _preprocess(preprocess_hook, payload)
        if postprocess_hook and preprocess_hook.status is not None:
            postprocess_hook.set_status(preprocess_hook.status)
    elif datatype is None:
        if payload is not None:
            return (payload, payload, postprocess_hook) if postprocess else payload
    elif not (datatype is DataObject or isinstance(payload, datatype)):
        return (payload, payload, postprocess_hook) if postprocess else payload

    on_queue, pp_result, pp_called = [payload], None, False
    for effective_event_name, event_info in effective_events.items():
        context = create_test_context(
            app_config, effective_event_name, track_ids=context.track_ids, auth_info=context.auth_info
        )
        stage_results = []
        for elem in on_queue:
            async for res in handler.handle_async_event(context=context, query_args=kwargs, payload=elem):
                stage_results.append(res)
        on_queue = stage_results if len(stage_results) > 0 else on_queue
        if postprocess_hook and not pp_called:
            pp_called = True
            pp_result = await _postprocess(postprocess_hook, on_queue)
        kwargs = {}

    if postprocess:
        if len(on_queue) == 0:
            return None, pp_result, postprocess_hook
        if len(on_queue) == 1:
            return on_queue[0], pp_result, postprocess_hook
        return list(on_queue), pp_result, postprocess_hook

    if len(on_queue) == 0:
        return None
    if len(on_queue) == 1:
        return on_queue[0]
    return list(on_queue)


async def execute_service(app_config: AppConfig,
                          event_name: str,
                          max_events: int = 1,
                          mocks: Optional[List[Callable[[ModuleType, EventContext], None]]] = None) \
        -> List[Union[EventPayload, Exception]]:
    """
    Executes __service__ handler of an event,
    and processes a maximum of `max_events`.
    :param app_config: AppConfig
    :param event_name: event_name, for a SERVICE event
    :param max_events: int, default 1, number of events to process as part of the test
    :param mocks: mocks to be forwarded to `execute_event`
    :return: List of results of processing available events
    """
    context = create_test_context(app_config, event_name)
    event_info = app_config.events[event_name]
    impl = find_event_handler(app_config=app_config, event_name=event_name, event_info=event_info)
    handler = getattr(impl, '__service__')
    count = 0
    results = []
    async for payload in handler(context):
        results.append(await execute_event(app_config, event_name, payload, mocks))
        count += 1
        if count >= max_events:
            break
    return results
