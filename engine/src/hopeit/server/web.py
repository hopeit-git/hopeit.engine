"""
Webserver module based on aiohttp to handle web/api requests
"""

# flake8: noqa
# pylint: disable=wrong-import-position, wrong-import-order
from collections import namedtuple

import aiohttp

setattr(aiohttp.http, "SERVER_SOFTWARE", "")

import argparse
import asyncio
import gc
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Type, Union

import aiohttp_cors  # type: ignore
from aiohttp import web
from aiohttp.web_response import Response
from aiohttp_cors import CorsConfig

from hopeit.app.config import (  # pylint: disable=ungrouped-imports
    AppConfig,
    EventDescriptor,
    EventPlugMode,
    EventSettings,
    EventType,
    parse_app_config_json,
)
from hopeit.app.context import (
    EventContext,
    NoopMultiparReader,
    PostprocessHook,
    PreprocessHook,
)
from hopeit.app.errors import BadRequest, Unauthorized
from hopeit.dataobjects import DataObject, EventPayload, EventPayloadType
from hopeit.dataobjects.payload import Payload
from hopeit.server import api, runtime
from hopeit.server.config import AuthType, ServerConfig, parse_server_config_json
from hopeit.server.engine import AppEngine
from hopeit.server.errors import ErrorInfo
from hopeit.server.events import get_event_settings
from hopeit.server.logger import (
    EngineLoggerWrapper,
    combined,
    engine_logger,
    extra_logger,
)
from hopeit.server.metrics import metrics
from hopeit.server.names import route_name
from hopeit.server.steps import find_datatype_handler
from hopeit.toolkit import auth

from stringcase import snakecase, titlecase  # type: ignore

__all__ = [
    "parse_args",
    "prepare_engine",
    "serve",
    "server_startup_hook",
    "app_startup_hook",
    "stream_startup_hook",
    "stop_server",
]

logger: EngineLoggerWrapper = logging.getLogger(__name__)  # type: ignore
extra = extra_logger()

ResponseType = Union[web.Response, web.FileResponse, web.StreamResponse]

web_server = web.Application()
auth_info_default = {}


def prepare_engine(
    *,
    config_files: List[str],
    api_file: Optional[str],
    api_auto: List[str],
    enabled_groups: List[str],
    start_streams: bool,
):
    """
    Load configuration files and add hooks to setup engine server and apps,
    start streams and services.
    """
    logger.info("Loading engine config file=%s...", config_files[0])  # type: ignore
    server_config: ServerConfig = _load_engine_config(config_files[0])

    # Add startup hook to start engine
    web_server.on_startup.append(partial(server_startup_hook, server_config))
    if server_config.auth.domain:
        auth_info_default["domain"] = server_config.auth.domain

    if api_file is not None:
        api.load_api_file(api_file)
        api.register_server_config(server_config)

    if api_file is None and api_auto:
        if len(api_auto) < 3:
            api_auto.extend(api.OPEN_API_DEFAULTS[len(api_auto) - 3 :])
        else:
            api_auto = api_auto[:3]
        api.init_auto_api(api_auto[0], api_auto[1], api_auto[2])
        api.register_server_config(server_config)

    apps_config = []
    for config_file in config_files[1:]:
        logger.info(__name__, f"Loading app config file={config_file}...")
        config = _load_app_config(config_file)
        config.server = server_config
        apps_config.append(config)

    # Register and add startup hooks to start configured apps
    api.register_apps(apps_config)
    api.enable_swagger(server_config, web_server)
    for config in apps_config:
        web_server.on_startup.append(partial(app_startup_hook, config, enabled_groups))

    # Add hooks to start streams and service
    if start_streams:
        for config in apps_config:
            web_server.on_startup.append(partial(stream_startup_hook, config))

    web_server.on_shutdown.append(_shutdown_hook)
    logger.debug(__name__, "Performing forced garbage collection...")
    gc.collect()


async def _shutdown_hook(app):
    logger.debug(__name__, "Calling shutdown hook...")
    await runtime.server.stop()
    logger.debug(__name__, "Done shutdown hook...")


def init_logger():
    global logger
    logger = engine_logger()


async def server_startup_hook(config: ServerConfig, *args, **kwargs):
    """
    Start engine engine
    """
    await runtime.server.start(config=config)
    init_logger()


async def stop_server():
    await runtime.server.stop()
    await web_server.shutdown()
    await web_server.cleanup()


async def app_startup_hook(config: AppConfig, enabled_groups: List[str], *args, **kwargs):
    """
    Start Hopeit app specified by config

    :param config: AppConfig, configuration for the app to start
    :param enabled_groups: list of event groups names to enable. If empty,
        all events will be enabled.
    """
    app_engine = await runtime.server.start_app(app_config=config, enabled_groups=enabled_groups)
    cors_origin = (
        aiohttp_cors.setup(
            web_server,
            defaults={
                config.engine.cors_origin: aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                )
            },
        )
        if config.engine.cors_origin
        else None
    )

    await _setup_app_event_routes(app_engine)
    for plugin in config.plugins:
        plugin_engine = runtime.server.app_engine(app_key=plugin.app_key())
        await _setup_app_event_routes(app_engine, plugin_engine)
    if cors_origin:
        app = app_engine.app_config.app
        cors_prefix = app_engine.app_config.engine.cors_routes_prefix
        if cors_prefix is None:
            cors_prefix = route_name("api", app.name, app.version)
        _enable_cors(cors_prefix, cors_origin)


async def stream_startup_hook(app_config: AppConfig, *args, **kwargs):
    """
    Start all stream event types configured in app.

    :param app_key: already started app_key
    """
    app_engine = runtime.server.app_engines[app_config.app_key()]
    for event_name, event_info in app_engine.effective_events.items():
        if event_info.type == EventType.STREAM:
            assert event_info.read_stream
            logger.info(
                __name__,
                f"STREAM start event_name={event_name} read_stream={event_info.read_stream.name}",
            )
            asyncio.create_task(app_engine.read_stream(event_name=event_name))
        elif event_info.type == EventType.SERVICE:
            logger.info(__name__, f"SERVICE start event_name={event_name}")
            asyncio.create_task(app_engine.service_loop(event_name=event_name))


def _effective_events(app_engine: AppEngine, plugin: Optional[AppEngine] = None):
    if plugin is None:
        return {
            k: v
            for k, v in app_engine.effective_events.items()
            if v.plug_mode == EventPlugMode.STANDALONE
        }
    return {k: v for k, v in plugin.effective_events.items() if v.plug_mode == EventPlugMode.ON_APP}


def _load_engine_config(path: str):
    """
    Load engine configuration from json file
    """
    with open(path, encoding="utf-8") as f:
        return parse_server_config_json(f.read())


def _load_app_config(path: str) -> AppConfig:
    """
    Load app configuration from json file
    """
    with open(path, encoding="utf-8") as f:
        return parse_app_config_json(f.read())


def _enable_cors(prefix: str, cors: CorsConfig):
    for route in web_server.router.routes():
        if route.resource and route.resource.canonical.startswith(prefix):
            cors.add(route)


async def _setup_app_event_routes(app_engine: AppEngine, plugin: Optional[AppEngine] = None):
    """
    Setup http routes for existing events in app,
    in existing web_server global instance.

    Supports:
    * GET requests with query params
    * POST requests with query params and payload sent in body
    * STREAM start/stop endpoints

    :param app_engine: AppEngine, initialized application engine
    :param cors: initialized CorsConfig object or None is CORS is disabled
    :param plugin: optional AppEngine, when the implementation of the route
        is handled by a plugin app, if not specified methods will be handled
        by same app_engine
    """
    for event_name, event_info in _effective_events(app_engine, plugin).items():
        if event_info.type == EventType.POST:
            web_server.add_routes(
                [
                    _create_post_event_route(
                        app_engine,
                        plugin=plugin,
                        event_name=event_name,
                        event_info=event_info,
                    )
                ]
            )
        elif event_info.type == EventType.GET:
            web_server.add_routes(
                [
                    _create_get_event_route(
                        app_engine,
                        plugin=plugin,
                        event_name=event_name,
                        event_info=event_info,
                    )
                ]
            )
        elif event_info.type == EventType.MULTIPART:
            web_server.add_routes(
                [
                    _create_multipart_event_route(
                        app_engine,
                        plugin=plugin,
                        event_name=event_name,
                        event_info=event_info,
                    )
                ]
            )
        elif event_info.type == EventType.STREAM and plugin is None:
            web_server.add_routes(
                _create_event_management_routes(
                    app_engine, event_name=event_name, event_info=event_info
                )
            )
        elif event_info.type == EventType.SERVICE and plugin is None:
            web_server.add_routes(
                _create_event_management_routes(
                    app_engine, event_name=event_name, event_info=event_info
                )
            )
        elif event_info.type == EventType.SETUP:
            await _execute_setup_event(app_engine, plugin, event_name)
        else:
            raise ValueError(f"Invalid event_type:{event_info.type} for event:{event_name}")


def _auth_types(app_engine: AppEngine, event_name: str):
    assert app_engine.app_config.server
    event_info = app_engine.app_config.events[event_name]
    if event_info.auth:
        return event_info.auth
    return app_engine.app_config.server.auth.default_auth_methods


def _create_post_event_route(
    app_engine: AppEngine,
    *,
    plugin: Optional[AppEngine] = None,
    event_name: str,
    event_info: EventDescriptor,
) -> web.RouteDef:
    """
    Creates route for handling POST event
    """
    datatype = find_datatype_handler(
        app_config=app_engine.app_config, event_name=event_name, event_info=event_info
    )
    route = api.app_route_name(
        app_engine.app_config.app,
        event_name=event_name,
        plugin=None if plugin is None else plugin.app_config.app,
        override_route_name=event_info.route,
    )
    logger.info(__name__, f"POST path={route} input={str(datatype)}")
    impl = plugin if plugin else app_engine
    handler = partial(
        _handle_post_invocation,
        app_engine,
        impl,
        event_name,
        datatype,
        _auth_types(impl, event_name),
    )
    setattr(handler, "__closure__", None)
    setattr(handler, "__code__", _handle_post_invocation.__code__)
    api_handler = api.add_route("post", route, handler)
    return web.post(route, api_handler)


def _create_get_event_route(
    app_engine: AppEngine,
    *,
    plugin: Optional[AppEngine] = None,
    event_name: str,
    event_info: EventDescriptor,
) -> web.RouteDef:
    """
    Creates route for handling GET requests
    """
    route = api.app_route_name(
        app_engine.app_config.app,
        event_name=event_name,
        plugin=None if plugin is None else plugin.app_config.app,
        override_route_name=event_info.route,
    )
    logger.info(__name__, f"GET path={route}")
    impl = plugin if plugin else app_engine
    handler = partial(
        _handle_get_invocation,
        app_engine,
        impl,
        event_name,
        _auth_types(impl, event_name),
    )
    setattr(handler, "__closure__", None)
    setattr(handler, "__code__", _handle_get_invocation.__code__)
    api_handler = api.add_route("get", route, handler)
    return web.get(route, api_handler)


def _create_multipart_event_route(
    app_engine: AppEngine,
    *,
    plugin: Optional[AppEngine] = None,
    event_name: str,
    event_info: EventDescriptor,
) -> web.RouteDef:
    """
    Creates route for handling MULTIPART event
    """
    datatype = find_datatype_handler(
        app_config=app_engine.app_config, event_name=event_name, event_info=event_info
    )
    route = api.app_route_name(
        app_engine.app_config.app,
        event_name=event_name,
        plugin=None if plugin is None else plugin.app_config.app,
        override_route_name=event_info.route,
    )
    logger.info(__name__, f"MULTIPART path={route} input={str(datatype)}")
    impl = plugin if plugin else app_engine
    handler = partial(
        _handle_multipart_invocation,
        app_engine,
        impl,
        event_name,
        datatype,
        _auth_types(impl, event_name),
    )
    setattr(handler, "__closure__", None)
    setattr(handler, "__code__", _handle_multipart_invocation.__code__)
    api_handler = api.add_route("post", route, handler)
    return web.post(route, api_handler)


def _create_event_management_routes(
    app_engine: AppEngine, *, event_name: str, event_info: EventDescriptor
) -> List[web.RouteDef]:
    """
    Create routes to start and stop processing of STREAM events
    """
    evt = event_name.replace(".", "/").replace("$", "/")
    base_route = api.app_route_name(
        app_engine.app_config.app,
        event_name=evt,
        prefix="mgmt",
        override_route_name=event_info.route,
    )
    logger.info(__name__, f"{event_info.type.value.upper()} path={base_route}/[start|stop]")

    handler: Optional[partial[Coroutine[Any, Any, Response]]] = None
    if event_info.type == EventType.STREAM:
        handler = partial(_handle_stream_start_invocation, app_engine, event_name)
    elif event_info.type == EventType.SERVICE:
        handler = partial(_handle_service_start_invocation, app_engine, event_name)
    assert handler is not None, f"No handler for event={event_name} type={event_info.type}"
    return [
        web.get(base_route + "/start", handler),
        web.get(
            base_route + "/stop",
            partial(_handle_event_stop_invocation, app_engine, event_name),
        ),
    ]


def _response(
    *, track_ids: Dict[str, str], key: str, payload: EventPayload, hook: PostprocessHook
) -> ResponseType:
    """
    Creates a web response object from a given payload (body), header track ids
    and applies a postprocess hook
    """
    response: ResponseType
    headers = {
        **hook.headers,
        **{f"X-{re.sub(' ', '-', titlecase(k))}": v for k, v in track_ids.items()},
    }
    if hook.file_response is not None:
        response = web.FileResponse(
            path=hook.file_response,
            headers={"Content-Type": hook.content_type, **headers},
        )
    elif hook.stream_response is not None:
        response = hook.stream_response.resp
    else:
        serializer: Callable[..., str] = CONTENT_TYPE_BODY_SER.get(
            hook.content_type, _text_response
        )
        body = serializer(payload, key=key)
        response = web.Response(body=body, headers=headers, content_type=hook.content_type)
        for name, cookie in hook.cookies.items():
            value, args, kwargs = cookie
            response.set_cookie(name, value, *args, **kwargs)
        for name, args, kwargs in hook.del_cookies:
            response.del_cookie(name, *args, **kwargs)
    if hook.status:
        response.set_status(hook.status)
    return response


def _response_info(response: ResponseType):
    return extra(prefix="response.", status=str(response.status))


def _track_ids(request: web.Request) -> Dict[str, str]:
    return {
        "track.operation_id": str(uuid.uuid4()),
        "track.request_id": str(uuid.uuid4()),
        "track.request_ts": datetime.now(tz=timezone.utc).isoformat(),
        **{
            "track." + snakecase(k[8:].lower()): v
            for k, v in request.headers.items()
            if k.lower().startswith("x-track-")
        },
    }


def _failed_response(context: Optional[EventContext], e: Exception) -> web.Response:
    if context:
        logger.error(context, e)
        logger.failed(context)
    else:
        logger.error(__name__, e)
    info = ErrorInfo.from_exception(e)
    return web.Response(status=500, body=Payload.to_json(info))


def _ignored_response(
    context: Optional[EventContext], status: int, e: BaseException
) -> web.Response:
    if context:
        logger.error(context, e)
        logger.ignored(context)
    else:
        logger.error(__name__, e)
    info = ErrorInfo.from_exception(e)
    return web.Response(status=status, body=Payload.to_json(info))


async def _execute_setup_event(
    app_engine: AppEngine,
    plugin: Optional[AppEngine],
    event_name: str,
) -> None:
    """
    Executes event of SETUP type, on server start
    """
    event_settings = get_event_settings(app_engine.settings, event_name)
    context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=app_engine.app_config if plugin is None else plugin.app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids={},
        auth_info=auth_info_default,
    )
    logger.start(context)

    if plugin is None:
        await app_engine.execute(context=context, query_args=None, payload=None)
    else:
        await plugin.execute(context=context, query_args=None, payload=None)

    logger.done(context, extra=metrics(context))


def _request_start(
    app_engine: AppEngine,
    plugin: AppEngine,
    event_name: str,
    event_settings: EventSettings,
    request: web.Request,
) -> EventContext:
    """
    Extracts context and track information from a request and logs start of event
    """
    context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=plugin.app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=_track_ids(request),
        auth_info=auth_info_default,
    )
    logger.start(context)
    return context


def _extract_auth_header(request: web.Request, context: EventContext) -> Optional[str]:
    return request.headers.get("Authorization")


def _extract_refresh_cookie(request: web.Request, context: EventContext) -> Optional[str]:
    return request.cookies.get(f"{context.app_key}.refresh")


def _ignore_auth(request: web.Request, context: EventContext) -> str:
    return "Unsecured -"


AUTH_HEADER_EXTRACTORS = {
    AuthType.BASIC: _extract_auth_header,
    AuthType.BEARER: _extract_auth_header,
    AuthType.REFRESH: _extract_refresh_cookie,
    AuthType.UNSECURED: _ignore_auth,
}


def _extract_authorization(
    auth_methods: List[AuthType], request: web.Request, context: EventContext
):
    for auth_type in auth_methods:
        auth_header = AUTH_HEADER_EXTRACTORS[auth_type](request, context)
        if auth_header is not None:
            return auth_header
    return "Unsecured -"


def _validate_authorization(
    app_config: AppConfig,
    context: EventContext,
    auth_types: List[AuthType],
    request: web.Request,
):
    """
    Validates Authorization header from request to provide valid credentials
    for the methods supported in event configuration.

    :raise `Unauthorized` if authorization is not valid
    """
    auth_methods = context.event_info.auth
    if (len(auth_methods) == 0) and (app_config.server is not None):
        auth_methods = app_config.server.auth.default_auth_methods
    auth_header = _extract_authorization(auth_methods, request, context)

    try:
        method, data = auth_header.split(" ")
    except ValueError as e:
        raise BadRequest("Malformed Authorization") from e

    context.auth_info["allowed"] = False
    for auth_type in auth_types:
        if method.upper() == auth_type.name.upper():
            auth.validate_auth_method(auth_type, data, context)
            if context.auth_info.get("allowed"):
                return None
    raise Unauthorized(method)


def _application_json_response(result: DataObject, key: str, *args, **kwargs) -> str:
    return Payload.to_json(result, key=key)


def _text_response(result: str, *args, **kwargs) -> str:
    return str(result)


CONTENT_TYPE_BODY_SER: Dict[str, Callable[..., str]] = {
    "application/json": _application_json_response,
    "text/html": _text_response,
    "text/plain": _text_response,
}


async def _request_execute(
    app_engine: AppEngine,
    event_name: str,
    context: EventContext,
    query_args: Dict[str, Any],
    payload: Optional[EventPayloadType],
    preprocess_hook: PreprocessHook,
    request: web.Request,
) -> ResponseType:
    """
    Executes request using engine event handler
    """
    response_hook = PostprocessHook(request)
    result = await app_engine.preprocess(
        context=context, query_args=query_args, payload=payload, request=preprocess_hook
    )
    if (preprocess_hook.status is None) or (preprocess_hook.status == 200):
        result = await app_engine.execute(context=context, query_args=query_args, payload=result)
        result = await app_engine.postprocess(
            context=context, payload=result, response=response_hook
        )
    else:
        response_hook.set_status(preprocess_hook.status)
    response = _response(
        track_ids=context.track_ids, key=event_name, payload=result, hook=response_hook
    )
    logger.done(context, extra=combined(_response_info(response), metrics(context)))
    return response


async def _request_process_payload(
    context: EventContext,
    datatype: Optional[Type[EventPayloadType]],
    request: web.Request,
) -> Tuple[Optional[EventPayloadType], Optional[bytes]]:
    """
    Extract payload from request.
    Returns payload if parsing succeeded. Raises BadRequest if payload fails to parse
    """
    try:
        payload_raw = await request.read()
        if datatype is not None:
            return Payload.from_json(payload_raw, datatype), payload_raw  # type: ignore
        return None, payload_raw
    except ValueError as e:
        logger.error(context, e)
        raise BadRequest(e) from e


async def _handle_post_invocation(
    app_engine: AppEngine,
    impl: AppEngine,
    event_name: str,
    datatype: Optional[Type[DataObject]],
    auth_types: List[AuthType],
    request: web.Request,
) -> ResponseType:
    """
    Handler to execute POST calls
    """
    context = None
    try:
        event_settings = get_event_settings(app_engine.settings, event_name)
        context = _request_start(app_engine, impl, event_name, event_settings, request)
        query_args = dict(request.query)
        _validate_authorization(app_engine.app_config, context, auth_types, request)
        payload, payload_raw = await _request_process_payload(context, datatype, request)
        hook: PreprocessHook[NoopMultiparReader] = PreprocessHook(
            headers=request.headers, payload_raw=payload_raw
        )
        return await _request_execute(
            impl,
            event_name,
            context,
            query_args,
            payload,
            preprocess_hook=hook,
            request=request,
        )
    except Unauthorized as e:
        return _ignored_response(context, 401, e)
    except BadRequest as e:
        return _ignored_response(context, 400, e)
    except Exception as e:  # pylint: disable=broad-except
        return _failed_response(context, e)


async def _handle_get_invocation(
    app_engine: AppEngine,
    impl: AppEngine,
    event_name: str,
    auth_types: List[AuthType],
    request: web.Request,
) -> ResponseType:
    """
    Handler to execute GET calls
    """
    context = None
    try:
        event_settings = get_event_settings(app_engine.settings, event_name)
        context = _request_start(app_engine, impl, event_name, event_settings, request)
        _validate_authorization(app_engine.app_config, context, auth_types, request)
        query_args = dict(request.query)
        payload = query_args.get("payload")
        if payload is not None:
            del query_args["payload"]
        hook: PreprocessHook[NoopMultiparReader] = PreprocessHook(headers=request.headers)
        return await _request_execute(
            impl,
            event_name,
            context,
            query_args,
            payload=payload,
            preprocess_hook=hook,
            request=request,
        )
    except Unauthorized as e:
        return _ignored_response(context, 401, e)
    except BadRequest as e:
        return _ignored_response(context, 400, e)
    except Exception as e:  # pylint: disable=broad-except
        return _failed_response(context, e)


async def _handle_multipart_invocation(
    app_engine: AppEngine,
    impl: AppEngine,
    event_name: str,
    datatype: Optional[Type[DataObject]],
    auth_types: List[AuthType],
    request: web.Request,
) -> ResponseType:
    """
    Handler to execute POST calls
    """
    context = None
    try:
        event_settings = get_event_settings(app_engine.settings, event_name)
        context = _request_start(app_engine, impl, event_name, event_settings, request)
        query_args = dict(request.query)
        _validate_authorization(app_engine.app_config, context, auth_types, request)
        hook = PreprocessHook(  # type: ignore
            headers=request.headers,
            multipart_reader=await request.multipart(),  # type: ignore
        )
        return await _request_execute(
            impl,
            event_name,
            context,
            query_args,
            payload=None,
            preprocess_hook=hook,
            request=request,
        )
    except Unauthorized as e:
        return _ignored_response(context, 401, e)
    except BadRequest as e:
        return _ignored_response(context, 400, e)
    except Exception as e:  # pylint: disable=broad-except
        return _failed_response(context, e)


async def _handle_stream_start_invocation(
    app_engine: AppEngine, event_name: str, request: web.Request
) -> web.Response:
    """
    Handles call to stream processing event `start` endpoint,
    spawning an async job that listens continuosly to event streams
    in the background.
    """
    assert request
    if app_engine.is_running(event_name):
        return web.Response(status=500, body=f"Stream already running: {event_name}")
    asyncio.create_task(app_engine.read_stream(event_name=event_name))
    return web.Response()


async def _handle_service_start_invocation(
    app_engine: AppEngine, event_name: str, request: web.Request
) -> web.Response:
    """
    Handles call to service event `start` endpoint,
    spawning an async job that listens continuosly __service__
    generator in the background
    """
    assert request
    if app_engine.is_running(event_name):
        return web.Response(status=500, body=f"Service already running: {event_name}")
    asyncio.create_task(app_engine.service_loop(event_name=event_name))
    return web.Response()


async def _handle_event_stop_invocation(
    app_engine: AppEngine, event_name: str, request: web.Request
) -> web.Response:
    """
    Signals engine for stopping an event.
    Used to stop reading stream processing events.
    """
    try:
        assert request
        await app_engine.stop_event(event_name)
        logger.info(__name__, f"Event stop signaled event_name={event_name}...")
        return web.Response()
    except RuntimeError as e:
        return web.Response(status=500, body=str(e))


ParsedArgs = namedtuple(
    "ParsedArgs",
    [
        "host",
        "port",
        "path",
        "start_streams",
        "config_files",
        "api_file",
        "api_auto",
        "enabled_groups",
    ],
)


def parse_args(args) -> ParsedArgs:
    """
    Parse command line arguments:
    param: args: in form of --arg=value
    --path, optional, is the path of posix socket
    --port, optional the tcp port number
    --start-streams, optional True if to auto start all events of STREAM type
    --config-files, is a comma-separated list of hopeit apps config files relative or full paths
    --api-file, optional path to openapi.json file with at least openapi and info sections
    --api-auto, optional when api_file is not defined, specify a semicolons-separated
              `version;title;description` to define API General Info and enable OpenAPI
    --enabled-groups, optional list of group label to be started
    Example::

        python web.py --port=8020 --path=/tmp/hopeit.01 --config-files=test.json

    Notes:
        --config-files argument is mandatory
        if --port and --path are not supplied the engine start on 8020 port by default

    """
    parser = argparse.ArgumentParser(description="hopeit.py engine")
    parser.add_argument("--host")
    parser.add_argument("--path")
    parser.add_argument("--port")
    parser.add_argument("--start-streams", action="store_true")
    parser.add_argument("--config-files")
    parser.add_argument("--api-file")
    parser.add_argument("--api-auto")
    parser.add_argument("--enabled-groups")

    parsed_args = parser.parse_args(args=args)
    port = int(parsed_args.port) if parsed_args.port else 8020 if parsed_args.path is None else None
    config_files = parsed_args.config_files.split(",")
    enabled_groups = parsed_args.enabled_groups.split(",") if parsed_args.enabled_groups else []
    api_auto = [] if parsed_args.api_auto is None else parsed_args.api_auto.split(";")

    return ParsedArgs(
        host=parsed_args.host,
        port=port,
        path=parsed_args.path,
        start_streams=bool(parsed_args.start_streams),
        config_files=config_files,
        api_file=parsed_args.api_file,
        api_auto=api_auto,
        enabled_groups=enabled_groups,
    )


def init_web_server(
    config_files: List[str],
    api_file: str,
    api_auto: List[str],
    enabled_groups: List[str],
    start_streams: bool,
) -> web.Application:
    """
    Init Web Server
    """
    if enabled_groups is None:
        enabled_groups = []
    prepare_engine(
        config_files=config_files,
        api_file=api_file,
        api_auto=api_auto,
        start_streams=start_streams,
        enabled_groups=enabled_groups,
    )
    return web_server


def serve(
    host: str,
    path: str,
    port: int,
    config_files: List[str],
    api_file: str,
    api_auto: List[str],
    start_streams: bool,
    enabled_groups: List[str],
):
    """
    Serve hopeit.engine
    """
    init_logger()

    web_app = init_web_server(config_files, api_file, api_auto, enabled_groups, start_streams)
    logger.info(__name__, f"Starting web server host: {host} port: {port} socket: {path}...")
    web.run_app(web_app, host=host, path=path, port=port)


if __name__ == "__main__":
    sys_args = parse_args(sys.argv[1:])
    serve(
        host=sys_args.host,
        path=sys_args.path,
        port=sys_args.port,
        config_files=sys_args.config_files,
        api_file=sys_args.api_file,
        api_auto=sys_args.api_auto,
        start_streams=sys_args.start_streams,
        enabled_groups=sys_args.enabled_groups,
    )
