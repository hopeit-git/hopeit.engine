"""
Webserver module based on aiohttp to handle web/api requests
"""
import argparse
import asyncio
import gc
import logging
import sys
# flake8: noqa
# pylint: disable=wrong-import-position, wrong-import-order
from collections import namedtuple
from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from hopeit.app.config import (
    AppConfig, EventPlugMode, EventType, parse_app_config_json
)
from hopeit.server import runtime
from hopeit.server.config import ServerConfig, parse_server_config_json
from hopeit.server.engine import AppEngine, Server
from hopeit.server.logger import (
    EngineLoggerWrapper, engine_logger, extra_logger
)
from engine.src.hopeit.server.imports import find_event_handler

__all__ = ['parse_args',
           'prepare_engine',
           'serve',
           'server_startup_hook',
           'app_startup_hook',
           'stream_startup_hook',
           'stop_server']

logger: EngineLoggerWrapper = logging.getLogger(__name__)  # type: ignore
extra = extra_logger()

# server = Server()
app = FastAPI()
auth_info_default = {}


@app.on_event("startup")
async def startup():
    await prepare_engine(config_files, None, [], False)


async def prepare_engine(config_files: List[str], api_file: Optional[str], enabled_groups: List[str], start_streams: bool):
    """
    Load configuration files and add hooks to setup engine server and apps,
    start streams and services.
    """
    logger.info("Loading engine config file=%s...", config_files[0])  # type: ignore
    server_config: ServerConfig = _load_engine_config(config_files[0])

    if server_config.auth.domain:
        auth_info_default['domain'] = server_config.auth.domain
    
    apps_config = []
    for config_file in config_files[1:]:
        logger.info(__name__, f"Loading app config file={config_file}...")
        config = _load_app_config(config_file)
        config.server = server_config
        apps_config.append(config)

    for config in apps_config:
        await app_startup_hook(config, enabled_groups)

    # Add hooks to start streams and service
    if start_streams:
        for config in apps_config:
            await stream_startup_hook(config)

    logger.debug(__name__, "Performing forced garbage collection...")
    gc.collect()


def serve(*, host: str, path: str, port: int):
    logger.info(__name__, f"Starting web server host: {host} port: {port} socket: {path}...")
    uvicorn.run(app)


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
    global app
    await runtime.server.stop()
    await app.shutdown()
    runtime.server = Server()
    app = web.Application()


async def app_startup_hook(config: AppConfig, enabled_groups: List[str], *args, **kwargs):
    """
    Start Hopeit app specified by config

    :param config: AppConfig, configuration for the app to start
    :param enabled_groups: list of event groups names to enable. If empty,
        all events will be enabled.
    """
    app_engine = await runtime.server.start_app(app_config=config, enabled_groups=enabled_groups)
    for event_name, event_info in config.events.items():
        impl = find_event_handler(app_config=config, event_name=event_name, event_info=event_info)
        router = getattr(impl, "api").get()
        app.include_router(router)


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
                __name__, f"STREAM start event_name={event_name} read_stream={event_info.read_stream.name}")
            asyncio.create_task(app_engine.read_stream(event_name=event_name))
        elif event_info.type == EventType.SERVICE:
            logger.info(
                __name__, f"SERVICE start event_name={event_name}")
            asyncio.create_task(app_engine.service_loop(event_name=event_name))


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


ParsedArgs = namedtuple("ParsedArgs", ["host", "port", "path", "start_streams",
                                       "config_files", "api_file", "enabled_groups"])


def parse_args(args) -> ParsedArgs:
    """
    Parse command line arguments:
    param: args: in form of --arg=value
    --path, optional, is the path of posix socket
    --port, optional the tcp port number
    --start-streams, optional True if to auto start all events of STREAM type
    --config-files, is a comma-separated list of hopeit apps config files relative or full paths
    --api-file, optional path to openapi.json file with at least openapi and info sections
    --enabled-groups, optional list of group label to be started
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
    parser.add_argument('--enabled-groups')

    parsed_args = parser.parse_args(args=args)
    port = int(parsed_args.port) if parsed_args.port else 8020 if parsed_args.path is None else None
    config_files = parsed_args.config_files.split(',')
    enabled_groups = parsed_args.enabled_groups.split(',') if parsed_args.enabled_groups else []

    return ParsedArgs(
        host=parsed_args.host,
        port=port,
        path=parsed_args.path,
        start_streams=bool(parsed_args.start_streams),
        config_files=config_files,
        api_file=parsed_args.api_file,
        enabled_groups=enabled_groups
    )


if __name__ == "__main__":
    sys_args = parse_args(sys.argv[1:])
    config_files = sys_args.config_files
    serve(host=sys_args.host, path=sys_args.path, port=sys_args.port)
