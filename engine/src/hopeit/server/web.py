"""
Webserver module based on aiohttp to handle web/api requests
"""
# flake8: noqa
# pylint: disable=wrong-import-position, wrong-import-order
import aiohttp
setattr(aiohttp.http, 'SERVER_SOFTWARE', '')

import sys
import re
import argparse
import uuid
import gc
from typing import Optional, Type, List, Dict, Tuple, Any, Union, Coroutine
from functools import partial
from datetime import datetime, timezone
import logging
import asyncio

from aiohttp import web
from aiohttp.web_response import Response
import aiohttp_cors  # type: ignore
from aiohttp_cors import CorsConfig
import aiojobs  # type: ignore
import aiojobs.aiohttp as aiojobs_http  # type: ignore
from aiojobs import Scheduler
from stringcase import snakecase, titlecase  # type: ignore

from hopeit.server import api
from hopeit.server.steps import find_datatype_handler
from hopeit.toolkit import auth
from hopeit.dataobjects.jsonify import Json
from hopeit.app.context import EventContext, NoopMultiparReader, PostprocessHook, PreprocessHook
from hopeit.dataobjects import DataObject, EventPayloadType
from hopeit.app.errors import Unauthorized, BadRequest
from hopeit.server.engine import Server, AppEngine
from hopeit.server.config import parse_server_config_json, ServerConfig, AuthType
from hopeit.server.logger import engine_logger, extra_logger, combined, EngineLoggerWrapper
from hopeit.server.metrics import metrics
from hopeit.server.errors import ErrorInfo
from hopeit.server.names import route_name
from hopeit.server.api import app_route_name
from hopeit.app.config import AppConfig, EventType, EventDescriptor, parse_app_config_json, EventPlugMode

__all__ = ['parse_args',
           'main',
           'start_server',
           'start_app',
           'stop_server']

logger: EngineLoggerWrapper = logging.getLogger(__name__)  # type: ignore
extra = extra_logger()

ResponseType = Union[web.Response, web.FileResponse]

server = Server()
web_server = web.Application()
aiojobs_http.setup(web_server)
auth_info_default = {}


def main(host: Optional[str], port: Optional[int], path: Optional[str], start_streams: bool,
         config_files: List[str], api_file: Optional[str]):
    loop = asyncio.get_event_loop()
    scheduler = loop.run_until_complete(aiojobs.create_scheduler())

    logger.info("Loading engine config file=%s...", config_files[0])  # type: ignore
    server_config = _load_engine_config(config_files[0])
    loop.run_until_complete(start_server(server_config))
    if server_config.auth.domain:
        auth_info_default['domain'] = server_config.auth.domain
    if api_file is not None:
        api.load_api_file(api_file)
        api.register_server_config(server_config)

    apps_config = []
    for config_file in config_files[1:]:
        logger.info(__name__, f"Loading app config file={config_file}...")
        config = _load_app_config(config_file)
        config.server = server_config
        apps_config.append(config)

    api.register_apps(apps_config)
    api.enable_swagger(server_config, web_server)
    for config in apps_config:
        loop.run_until_complete(start_app(config, scheduler, start_streams))

    logger.debug(__name__, "Performing forced garbage collection...")
    gc.collect()
    web.run_app(web_server, path=path, port=port, host=host)


def init_logger():
    global logger
    logger = engine_logger()


async def start_server(config: ServerConfig):
    """
    Start engine engine
    """
    global server
    server = await Server().start(config=config)
    init_logger()


async def stop_server():
    global server, web_server
    await server.stop()
    server = Server()
    await web_server.shutdown()
    web_server = web.Application()


async def start_app(config: AppConfig, scheduler: Scheduler, start_streams: bool = False):
    """
    Start Hopeit app specified by config

    :param config: AppConfig, configuration for the app to start
    :param start_streams: if True all stream events in app will start consuming
    """
    app_engine = await server.start_app(app_config=config)
    cors_origin = aiohttp_cors.setup(web_server, defaults={
        config.engine.cors_origin: aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    }) if config.engine.cors_origin else None

    _setup_app_event_routes(app_engine)
    for plugin in config.plugins:
        plugin_engine = server.app_engine(app_key=plugin.app_key())
        _setup_app_event_routes(app_engine, plugin_engine)
    if cors_origin:
        app = app_engine.app_config.app
        _enable_cors(route_name('api', app.name, app.version), cors_origin)
    if start_streams:
        await _start_streams(app_engine, scheduler)


def _effective_events(app_engine: AppEngine, plugin: Optional[AppEngine] = None):
    if plugin is None:
        return {
            k: v for k, v in app_engine.effective_events.items()
            if v.plug_mode == EventPlugMode.STANDALONE
        }
    return {
        k: v for k, v in plugin.effective_events.items()
        if v.plug_mode == EventPlugMode.ON_APP
    }


def _load_engine_config(path: str):
    """
    Load engine configuration from json file
    """
    with open(path) as f:
        return parse_server_config_json(f.read())


def _load_app_config(path: str):
    """
    Load app configuration from json file
    """
    with open(path) as f:
        return parse_app_config_json(f.read())


def _enable_cors(prefix: str, cors: CorsConfig):
    for route in web_server.router.routes():
        if route.resource and route.resource.canonical.startswith(prefix):
            cors.add(route)


def _setup_app_event_routes(app_engine: AppEngine,
                            plugin: Optional[AppEngine] = None):
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
            web_server.add_routes([
                _create_post_event_route(
                    app_engine, plugin=plugin, event_name=event_name, override_route_name=event_info.route
                )
            ])
        elif event_info.type == EventType.GET:
            web_server.add_routes([
                _create_get_event_route(
                    app_engine, plugin=plugin, event_name=event_name, override_route_name=event_info.route
                )
            ])
        elif event_info.type == EventType.MULTIPART:
            web_server.add_routes([
                _create_multipart_event_route(
                    app_engine, plugin=plugin, event_name=event_name, override_route_name=event_info.route
                )
            ])
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
        else:
            raise ValueError(f"Invalid event_type:{event_info.type} for event:{event_name}")


def _auth_types(app_engine: AppEngine, event_name: str):
    assert app_engine.app_config.server
    event_info = app_engine.app_config.events[event_name]
    if event_info.auth:
        return event_info.auth
    return app_engine.app_config.server.auth.default_auth_methods


def _create_post_event_route(
        app_engine: AppEngine, *,
        plugin: Optional[AppEngine] = None,
        event_name: str,
        override_route_name: Optional[str]) -> web.RouteDef:
    """
    Creates route for handling POST event
    """
    datatype = find_datatype_handler(app_config=app_engine.app_config, event_name=event_name)
    route = app_route_name(app_engine.app_config.app, event_name=event_name,
                           plugin=None if plugin is None else plugin.app_config.app,
                           override_route_name=override_route_name)
    logger.info(__name__, f"POST path={route} input={str(datatype)}")
    impl = plugin if plugin else app_engine
    handler = partial(_handle_post_invocation, app_engine, impl,
                      event_name, datatype, _auth_types(impl, event_name))
    setattr(handler, '__closure__', None)
    setattr(handler, '__code__', _handle_post_invocation.__code__)
    api_handler = api.add_route('post', route, handler)
    return web.post(route, api_handler)


def _create_get_event_route(
        app_engine: AppEngine, *,
        plugin: Optional[AppEngine] = None,
        event_name: str,
        override_route_name: Optional[str]) -> web.RouteDef:
    """
    Creates route for handling GET requests
    """
    route = app_route_name(app_engine.app_config.app, event_name=event_name,
                           plugin=None if plugin is None else plugin.app_config.app,
                           override_route_name=override_route_name)
    logger.info(__name__, f"GET path={route}")
    impl = plugin if plugin else app_engine
    handler = partial(_handle_get_invocation, app_engine, impl, event_name, _auth_types(impl, event_name))
    setattr(handler, '__closure__', None)
    setattr(handler, '__code__', _handle_post_invocation.__code__)
    api_handler = api.add_route('get', route, handler)
    return web.get(route, api_handler)


def _create_multipart_event_route(
        app_engine: AppEngine, *,
        plugin: Optional[AppEngine] = None,
        event_name: str,
        override_route_name: Optional[str]) -> web.RouteDef:
    """
    Creates route for handling MULTIPART event
    """
    datatype = find_datatype_handler(app_config=app_engine.app_config, event_name=event_name)
    route = app_route_name(app_engine.app_config.app, event_name=event_name,
                           plugin=None if plugin is None else plugin.app_config.app,
                           override_route_name=override_route_name)
    logger.info(__name__, f"MULTIPART path={route} input={str(datatype)}")
    impl = plugin if plugin else app_engine
    handler = partial(_handle_multipart_invocation, app_engine, impl,
                      event_name, datatype, _auth_types(impl, event_name))
    setattr(handler, '__closure__', None)
    setattr(handler, '__code__', _handle_multipart_invocation.__code__)
    api_handler = api.add_route('post', route, handler)
    return web.post(route, api_handler)


def _create_event_management_routes(
        app_engine: AppEngine, *,
        event_name: str,
        event_info: EventDescriptor) -> List[web.RouteDef]:
    """
    Create routes to start and stop processing of STREAM events
    """
    app = app_engine.app_config.app
    base_route = app_route_name(app_engine.app_config.app, event_name=event_name,
                                prefix='mgmt', override_route_name=event_info.route)
    logger.info(__name__, f"{event_info.type.value.upper()} path={base_route}/[start|stop]")

    handler: Optional[partial[Coroutine[Any, Any, Response]]] = None
    if event_info.type == EventType.STREAM:
        handler = partial(_handle_stream_start_invocation, app_engine, event_name)
    elif event_info.type == EventType.SERVICE:
        handler = partial(_handle_service_start_invocation, app_engine, event_name)
    assert handler is not None, f"No handler for event={event_name} type={event_info.type}"
    return [
        web.get(route_name('mgmt', app.name, app.version, event_name.replace('.', '/'), 'start'), handler),
        web.get(
            route_name('mgmt', app.name, app.version, event_name.replace('.', '/'), 'stop'),
            partial(_handle_event_stop_invocation, app_engine, event_name)
        )
    ]


def _response(*, track_ids: Dict[str, str], body: str, hook: PostprocessHook) -> ResponseType:
    """
    Creates a web response object from a given payload (body), header track ids
    and applies a postprocess hook
    """
    response: ResponseType
    headers = {
        **hook.headers,
        **{f"X-{re.sub(' ', '-', titlecase(k))}": v for k, v in track_ids.items()}
    }
    if hook.file_response is not None:
        response = web.FileResponse(
            path=hook.file_response,
            headers=headers
        )
    else:
        response = web.Response(
            body=body,
            headers=headers,
            content_type='application/json'
        )
        for name, cookie in hook.cookies.items():
            value, args, kwargs = cookie
            response.set_cookie(name, value, *args, **kwargs)
        for name, args, kwargs in hook.del_cookies:
            response.del_cookie(name, *args, **kwargs)
    if hook.status:
        response.set_status(hook.status)
    return response


def _response_info(response: ResponseType):
    return extra(prefix='response.', status=str(response.status))


def _track_ids(request: web.Request) -> Dict[str, str]:
    return {
        'track.operation_id': str(uuid.uuid4()),
        'track.request_id': str(uuid.uuid4()),
        'track.request_ts': datetime.now().astimezone(timezone.utc).isoformat(),
        **{
            "track." + snakecase(k[8:].lower()): v
            for k, v in request.headers.items() if k.lower().startswith('x-track-')
        }
    }


def _failed_response(context: Optional[EventContext],
                     e: Exception) -> web.Response:
    if context:
        logger.error(context, e)
        logger.failed(context)
    else:
        logger.error(__name__, e)
    info = ErrorInfo.from_exception(e)
    return web.Response(
        status=500,
        body=Json.to_json(info)
    )


def _ignored_response(context: Optional[EventContext],
                      status: int,
                      e: BaseException) -> web.Response:
    if context:
        logger.error(context, e)
        logger.ignored(context)
    else:
        logger.error(__name__, e)
    info = ErrorInfo.from_exception(e)
    return web.Response(
        status=status,
        body=Json.to_json(info)
    )


def _request_start(app_engine: AppEngine,
                   plugin: AppEngine,
                   event_name: str,
                   request: web.Request) -> EventContext:
    """
    Extracts context and track information from a request and logs start of event
    """
    context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=plugin.app_config,
        event_name=event_name,
        track_ids=_track_ids(request),
        auth_info=auth_info_default
    )
    logger.start(context)
    return context


def _extract_auth_header(request: web.Request, context: EventContext) -> Optional[str]:
    return request.headers.get("Authorization")


def _extract_refresh_cookie(request: web.Request, context: EventContext) -> Optional[str]:
    return request.cookies.get(f"{context.app_key}.refresh")


def _ignore_auth(request: web.Request, context: EventContext) -> str:
    return 'Unsecured -'


AUTH_HEADER_EXTRACTORS = {
    AuthType.BASIC: _extract_auth_header,
    AuthType.BEARER: _extract_auth_header,
    AuthType.REFRESH: _extract_refresh_cookie,
    AuthType.UNSECURED: _ignore_auth
}


def _extract_authorization(auth_methods: List[AuthType], request: web.Request, context: EventContext):
    for auth_type in auth_methods:
        auth_header = AUTH_HEADER_EXTRACTORS[auth_type](request, context)
        if auth_header is not None:
            return auth_header
    return 'Unsecured -'


def _validate_authorization(app_config: AppConfig,
                            context: EventContext,
                            auth_types: List[AuthType],
                            request: web.Request):
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
    for auth_type in auth_types:
        if method.upper() == auth_type.name.upper():
            auth.validate_auth_method(auth_type, data, context)
            if context.auth_info.get('allowed'):
                return None
    raise Unauthorized(method)


async def _request_execute(
        app_engine: AppEngine,
        event_name: str,
        context: EventContext,
        query_args: Dict[str, Any],
        payload: Optional[EventPayloadType],
        preprocess_hook: PreprocessHook) -> ResponseType:
    """
    Executes request using engine event handler
    """
    response_hook = PostprocessHook()
    result = await app_engine.preprocess(
        context=context, query_args=query_args, payload=payload, request=preprocess_hook)
    if (preprocess_hook.status is None) or (preprocess_hook.status == 200):
        result = await app_engine.execute(
            context=context, query_args=query_args, payload=result)
        result = await app_engine.postprocess(context=context, payload=result, response=response_hook)
    else:
        response_hook.set_status(preprocess_hook.status)
    body = Json.to_json(result, key=event_name)
    response = _response(track_ids=context.track_ids, body=body, hook=response_hook)
    logger.done(context, extra=combined(
        _response_info(response), metrics(context)
    ))
    return response


async def _request_process_payload(
        context: EventContext,
        datatype: Optional[Type[EventPayloadType]],
        request: web.Request) -> Optional[EventPayloadType]:
    """
    Extract payload from request.
    Returns payload if parsing succeeded. Raises BadRequest if payload fails to parse
    """
    try:
        payload_raw = await request.read()
        if (payload_raw is None) or (payload_raw == b''):
            return None
        payload = Json.from_json(payload_raw, datatype) if datatype else payload_raw.decode()
        return payload  # type: ignore
    except ValueError as e:
        logger.error(context, e)
        raise BadRequest(e) from e


async def _handle_post_invocation(
        app_engine: AppEngine,
        impl: AppEngine,
        event_name: str,
        datatype: Optional[Type[DataObject]],
        auth_types: List[AuthType],
        request: web.Request) -> ResponseType:
    """
    Handler to execute POST calls
    """
    context = None
    try:
        context = _request_start(app_engine, impl, event_name, request)
        query_args = dict(request.query)
        _validate_authorization(app_engine.app_config, context, auth_types, request)
        payload = await _request_process_payload(context, datatype, request)
        hook: PreprocessHook[NoopMultiparReader] = PreprocessHook(headers=request.headers)
        return await _request_execute(impl, event_name, context, query_args, payload, preprocess_hook=hook)
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
        request: web.Request) -> ResponseType:
    """
    Handler to execute GET calls
    """
    context = None
    try:
        context = _request_start(app_engine, impl, event_name, request)
        _validate_authorization(app_engine.app_config, context, auth_types, request)
        query_args = dict(request.query)
        payload = query_args.get('payload')
        if payload is not None:
            del query_args['payload']
        hook: PreprocessHook[NoopMultiparReader] = PreprocessHook(headers=request.headers)
        return await _request_execute(impl, event_name, context, query_args, payload=payload,
                                      preprocess_hook=hook)
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
        request: web.Request) -> ResponseType:
    """
    Handler to execute POST calls
    """
    context = None
    try:
        context = _request_start(app_engine, impl, event_name, request)
        query_args = dict(request.query)
        _validate_authorization(app_engine.app_config, context, auth_types, request)
        hook = PreprocessHook(                                                   # type: ignore
            headers=request.headers, multipart_reader=await request.multipart()  # type: ignore
        )
        return await _request_execute(impl, event_name, context, query_args, payload=None,
                                      preprocess_hook=hook)
    except Unauthorized as e:
        return _ignored_response(context, 401, e)
    except BadRequest as e:
        return _ignored_response(context, 400, e)
    except Exception as e:  # pylint: disable=broad-except
        return _failed_response(context, e)

async def _start_streams(app_engine: AppEngine, scheduler: Scheduler):
    """
    Start all stream event types configured in app.

    :param app_engine: already started instance of AppEngine
    """
    for event_name, event_info in app_engine.effective_events.items():
        if event_info.type == EventType.STREAM:
            assert event_info.read_stream
            logger.info(
                __name__, f"STREAM start event_name={event_name} read_stream={event_info.read_stream.name}")
            await scheduler.spawn(app_engine.read_stream(event_name=event_name))
        elif event_info.type == EventType.SERVICE:
            logger.info(
                __name__, f"SERVICE start event_name={event_name}")
            await scheduler.spawn(app_engine.service_loop(event_name=event_name))



async def _handle_stream_start_invocation(
        app_engine: AppEngine,
        event_name: str,
        request: web.Request) -> web.Response:
    """
    Handles call to stream processing event `start` endpoint,
    spawning an async job that listens continuosly to event streams
    in the background.
    """
    assert request
    await aiojobs_http.spawn(request, app_engine.read_stream(event_name=event_name))
    return web.Response()


async def _handle_service_start_invocation(
        app_engine: AppEngine,
        event_name: str,
        request: web.Request) -> web.Response:
    """
    Handles call to service event `start` endpoint,
    spawning an async job that listens continuosly __service__
    generator in the background
    """
    assert request
    await aiojobs_http.spawn(request, app_engine.service_loop(event_name=event_name))
    return web.Response()


async def _handle_event_stop_invocation(
        app_engine: AppEngine,
        event_name: str,
        request: web.Request) -> web.Response:
    """
    Signals engine for stopping an event.
    Used to stop reading stream processing events.
    """
    assert request
    await app_engine.stop_event(event_name)
    logger.info(__name__, f"Event stop signaled event_name={event_name}...")
    return web.Response()


def parse_args(args) -> Tuple[Optional[str], Optional[int], Optional[str], bool, List[str], Optional[str]]:
    """
    Parse command line arguments:
    param: args: in form of --arg=value
    --path, optional, is the path of posix socket
    --port, optional the tcp port number
    --start-streams, optional True if to auto start all events of STREAM type
    --config-files, is a comma-separated list of hopeit apps config files relative or full paths
    --api-file, optional path to openapi.json file with at least openapi and info sections
    Example::

        python web.py --port=8020 --path=/tmp/hopeit.01 --config-files=test.json

    Notes:
        --config-files argument is mandatory
        if --port and --path are not supplied the engine start on 8020 port by default

    """
    parser = argparse.ArgumentParser(description="hopeit.py engine")
    parser.add_argument('--host')
    parser.add_argument('--path')
    parser.add_argument('--port')
    parser.add_argument('--start-streams', action='store_true')
    parser.add_argument('--config-files')
    parser.add_argument('--api-file')

    parsed_args = parser.parse_args(args=args)
    port = int(parsed_args.port) if parsed_args.port else 8020 if parsed_args.path is None else None
    config_files = parsed_args.config_files.split(',')

    return parsed_args.host, port, parsed_args.path, bool(parsed_args.start_streams), \
        config_files, parsed_args.api_file


if __name__ == "__main__":
    sys_args = parse_args(sys.argv[1:])
    main(*sys_args)
