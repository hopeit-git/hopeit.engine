"""
Test utilities/wrappers for app development
"""
from pathlib import Path
from types import ModuleType
from typing import Union, Callable, List, Optional, Dict, Tuple
from datetime import datetime, timezone

from hopeit.app.config import AppConfig, parse_app_config_json, EventDescriptor
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import EventPayload
from hopeit.server.config import AuthType, ServerConfig, LoggingConfig
from hopeit.server.events import EventHandler
from hopeit.server.steps import split_event_stages, find_datatype_handler
from hopeit.server.imports import find_event_handler
from hopeit.server.logger import engine_logger

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
    with open(path, 'r') as f:
        app_config = parse_app_config_json(f.read())
        app_config.server = server_config()
        return app_config


def server_config():
    return ServerConfig(
        logging=LoggingConfig(log_level='DEBUG', log_path='logs/')
    )


def create_test_context(app_config: AppConfig, event_name: str) -> EventContext:
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name=event_name,
        track_ids={
            'track.operation_id': 'test_operation_id',
            'track.request_id': 'test_request_id',
            'track.request_ts': datetime.now(tz=timezone.utc).isoformat()
        },
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )


def _apply_mocks(context: EventContext,
                 handler: EventHandler,
                 event_name: str,
                 effective_events: Dict[str, EventDescriptor],
                 mocks: List[Callable[[ModuleType, EventContext], None]]):
    """
    Execute a list of functions to mock module properties.
    """
    module, _, _ = handler.modules[event_name]
    logger.debug(context, f"[test.apps] executing mocks for module={module.__name__}...")
    for mock in mocks:
        mock(module, context)
    handler.load_modules(effective_events=effective_events)
    logger.debug(context, '[test.apps] mocking done.')


async def execute_event(app_config: AppConfig,
                        event_name: str,
                        payload: Optional[EventPayload],
                        mocks: Optional[List[Callable[[ModuleType, EventContext], None]]] = None,
                        postprocess: bool = False,
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
    :param kwargs: that will be forwarded to the initial step of the event
    :return: the results of executing the event, for simple events it will be a single object,
        for events with initial Spawn[...] the results will be collected as a list.
        If postprocess is true, a tuple of 3 elements is return, first element is results as described
        above, second element the output of call to __postprocess__, and third one a PostprocessHook
        with response information used during call to __postprocess__
    """
    async def _postprocess(results: List[EventPayload]) -> Tuple[EventPayload, PostprocessHook]:
        pp_payload = results[-1] if len(results) > 0 else None
        hook = PostprocessHook()
        pp_result = await handler.postprocess(context=context, payload=pp_payload, response=hook)
        return pp_result, hook

    context = create_test_context(app_config, event_name)
    impl = find_event_handler(app_config=app_config, event_name=event_name)
    datatype = find_datatype_handler(app_config=app_config, event_name=event_name)
    if datatype is None:
        if payload is not None:
            raise ValueError("Invalid payload. Expected None")
    elif not isinstance(payload, datatype):
        raise ValueError(f"Invalid payload type={type(payload).__name__}. Expected type={datatype.__name__}")
    event_info = app_config.events[event_name]
    effective_events = {**split_event_stages(app_config.app, event_name, event_info, impl)}
    handler = EventHandler(app_config=app_config, plugins=[],
                           effective_events=effective_events)
    if mocks is not None:
        _apply_mocks(context, handler, event_name, effective_events, mocks)
    on_queue, pp_result, response = [payload], None, None
    for effective_event_name, event_info in effective_events.items():
        context = create_test_context(app_config, effective_event_name)
        stage_results = []
        for elem in on_queue:
            async for res in handler.handle_async_event(context=context, query_args=kwargs, payload=elem):
                stage_results.append(res)
        on_queue = stage_results if len(stage_results) > 0 else on_queue
        if postprocess and response is None:
            pp_result, response = await _postprocess(on_queue)
        kwargs = {}

    if postprocess:
        if len(on_queue) == 0:
            return None, pp_result, response
        if len(on_queue) == 1:
            return on_queue[0], pp_result, response
        return list(on_queue), pp_result, response

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
    impl = find_event_handler(app_config=app_config, event_name=event_name)
    handler = getattr(impl, '__service__')
    count = 0
    results = []
    async for payload in handler(context):
        results.append(await execute_event(app_config, event_name, payload, mocks))
        count += 1
        if count >= max_events:
            break
    return results
