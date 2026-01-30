"""
Job runner module to execute a single event without starting a web server.
"""

from collections import namedtuple
import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Type

from multidict import CIMultiDict, CIMultiDictProxy

from hopeit.app.config import (
    AppConfig,
    EventDescriptor,
    EventPlugMode,
    EventSettings,
    EventType,
)
from hopeit.app.config import parse_app_config_json
from hopeit.app.context import EventContext, PostprocessHook, PreprocessHook
from hopeit.dataobjects import EventPayload, EventPayloadType
from hopeit.dataobjects.payload import Payload
from hopeit.server import runtime
from hopeit.server.config import ServerConfig, parse_server_config_json
from hopeit.server.engine import AppEngine
from hopeit.server.events import get_event_settings
from hopeit.server.logger import engine_logger
from hopeit.server.metrics import metrics
from hopeit.server.steps import event_and_step, find_datatype_handler

__all__ = ["parse_args", "resolve_payload", "run_job"]

logger = engine_logger()

ParsedArgs = namedtuple(
    "ParsedArgs",
    [
        "config_files",
        "event_name",
        "payload",
        "start_streams",
        "max_events",
    ],
)


def _read_payload_source(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    with open(source, "r", encoding="utf-8") as f:
        return f.read()


def resolve_payload(payload: Optional[str], input_file: Optional[str]) -> Optional[str]:
    """
    Returns payload string, optionally reading content from file.
    Supports curl syntax with @file or @- for stdin.
    """
    if input_file:
        source = input_file[1:] if input_file.startswith("@") else input_file
        return _read_payload_source(source)
    if payload and payload.startswith("@"):
        source = payload[1:]
        if not source:
            raise ValueError("Payload file path missing after '@'.")
        return _read_payload_source(source)
    return payload


def parse_args(args) -> ParsedArgs:
    """
    Parse command line arguments:
    --config-files: comma-separated list of server, plugins and app config files
    --event-name: event name to execute
    --payload: json string payload, optionally use @file or @- for stdin
    --input-file: read payload from file (same as --payload=@file)
    --start-streams: enable stream-related execution (STREAM events / SHUFFLE chains)
    --max-events: limit number of consumed events for STREAM runs
    """
    parser = argparse.ArgumentParser(description="hopeit job runner")
    parser.add_argument("--config-files", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--payload")
    parser.add_argument("--input-file")
    parser.add_argument("--start-streams", action="store_true")
    parser.add_argument("--max-events", type=int)

    parsed_args = parser.parse_args(args=args)
    payload = resolve_payload(parsed_args.payload, parsed_args.input_file)

    return ParsedArgs(
        config_files=parsed_args.config_files.split(","),
        event_name=parsed_args.event_name,
        payload=payload,
        start_streams=bool(parsed_args.start_streams),
        max_events=parsed_args.max_events,
    )


def _load_engine_config(path: str) -> ServerConfig:
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


def _select_app_config(app_configs: List[AppConfig], event_name: str) -> AppConfig:
    """
    Find the single app config that owns the base event name.
    Raises if not found or if multiple apps define the same event.
    """
    base_event, _ = event_and_step(event_name)
    matches = [config for config in app_configs if base_event in config.events]
    if len(matches) == 0:
        raise ValueError(f"Event not found: {event_name}")
    if len(matches) > 1:
        app_keys = ", ".join(config.app_key() for config in matches)
        raise ValueError(f"Event '{event_name}' found in multiple apps: {app_keys}")
    return matches[0]


def _plugins_for_app(app_config: AppConfig, app_configs: List[AppConfig]) -> List[AppConfig]:
    """
    Resolve plugin configs required by an app, preserving app plugin order.
    Raises if any plugin config is missing from the provided config list.
    """
    configs_by_key = {config.app_key(): config for config in app_configs}
    plugins: List[AppConfig] = []
    for plugin in app_config.plugins:
        key = plugin.app_key()
        if key not in configs_by_key:
            raise ValueError(f"Missing plugin config for app_key={key}")
        plugins.append(configs_by_key[key])
    return plugins


def _create_context(
    *,
    app_config: AppConfig,
    event_name: str,
    event_settings: EventSettings,
) -> EventContext:
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=_job_track_ids(app_config, event_name),
        auth_info={},
    )


def _parse_payload(
    payload: Optional[str],
    datatype: Optional[Type[EventPayloadType]],
) -> Tuple[Optional[EventPayloadType], Optional[bytes]]:
    if payload is None:
        return None, None
    payload_raw = payload.encode()
    if datatype is None:
        return None, payload_raw
    return Payload.from_json(payload_raw, datatype), payload_raw  # type: ignore


async def _execute_event(
    *,
    app_engine,
    event_name: str,
    event_info: EventDescriptor,
    payload: Optional[str],
) -> Optional[EventPayload]:
    event_settings = get_event_settings(app_engine.settings, event_name)
    context = _create_context(
        app_config=app_engine.app_config,
        event_name=event_name,
        event_settings=event_settings,
    )
    try:
        logger.start(context)

        datatype = find_datatype_handler(
            app_config=app_engine.app_config,
            event_name=event_name,
            event_info=event_info,
        )
        parsed_payload, payload_raw = _parse_payload(payload, datatype)

        preprocess_hook: PreprocessHook = PreprocessHook(
            headers=CIMultiDictProxy(CIMultiDict()),
            payload_raw=payload_raw,
        )
        result = await app_engine.preprocess(
            context=context,
            query_args=None,
            payload=parsed_payload,
            request=preprocess_hook,
        )
        if (preprocess_hook.status is None) or (preprocess_hook.status == 200):
            result = await app_engine.execute(context=context, query_args=None, payload=result)
            result = await app_engine.postprocess(
                context=context, payload=result, response=PostprocessHook()
            )
        else:
            result = None
        logger.done(context, extra=metrics(context))
        return result
    except Exception as e:  # pylint: disable=broad-except
        logger.error(context, e)
        logger.failed(context, extra=metrics(context))
        raise


async def run_job(
    *,
    config_files: List[str],
    event_name: str,
    payload: Optional[str] = None,
    start_streams: bool = False,
    max_events: Optional[int] = None,
) -> Optional[EventPayload]:
    """
    Starts engine and apps from config files and executes a single event.

    Only GET, POST and STREAM events are supported.
    """
    if len(config_files) < 2:
        raise ValueError("config_files must include server config and at least one app config")

    server_config = _load_engine_config(config_files[0])
    app_configs = [_load_app_config(path) for path in config_files[1:]]
    for config in app_configs:
        config.server = server_config
    owner_config = _select_app_config(app_configs, event_name)

    await runtime.server.start(config=server_config)
    background_tasks: List[Tuple[AppEngine, str, asyncio.Task]] = []
    try:
        for config in app_configs:
            logger.info(__name__, f"Starting app={config.app_key()}...")
            app_engine = await AppEngine(
                app_config=config,
                plugins=_plugins_for_app(config, app_configs),
                enabled_groups=[],
                stop_wait_on_streams=False,
            ).start(init_auth=False)
            runtime.server.app_engines[config.app_key()] = app_engine

        app_engine = runtime.server.app_engines[owner_config.app_key()]
        await _run_setup_events(app_engine)
        for plugin in owner_config.plugins:
            plugin_engine = runtime.server.app_engines[plugin.app_key()]
            await _run_setup_events(
                app_engine, plugin_engine=plugin_engine, plug_mode=EventPlugMode.ON_APP
            )
        event_info = app_engine.effective_events[event_name]

        if event_info.type in (EventType.GET, EventType.POST):
            if event_info.write_stream is not None:
                if not start_streams:
                    logger.warning(
                        __name__,
                        "Event '%s' writes to stream; use --start-streams to enable stream consumers.",
                        event_name,
                    )
                    raise NotImplementedError(
                        f"Stream-related events require --start-streams: {event_name}"
                    )
                background_tasks = _start_related_streams(
                    app_engine=app_engine,
                    event_name=event_name,
                )
                await _wait_streams_ready(
                    background_tasks, server_config.streams.delay_auto_start_seconds
                )
            return await _execute_event(
                app_engine=app_engine,
                event_name=event_name,
                event_info=event_info,
                payload=payload,
            )

        if event_info.type == EventType.STREAM:
            if event_info.read_stream is None:
                if event_info.write_stream is not None:
                    logger.info(
                        __name__,
                        "STREAM event has no read_stream; producing only to %s.",
                        event_info.write_stream.name,
                    )
                return await _execute_event(
                    app_engine=app_engine,
                    event_name=event_name,
                    event_info=event_info,
                    payload=payload,
                )
            if not start_streams:
                logger.warning(
                    __name__,
                    "STREAM events require --start-streams: %s",
                    event_name,
                )
                raise NotImplementedError(f"STREAM events require --start-streams: {event_name}")
            if payload is not None:
                logger.warning(
                    __name__,
                    "STREAM events consume from streams; payload was provided and will be ignored.",
                )
                return None
            return await app_engine.consume_stream(
                event_name=event_name,
                max_events=max_events,
            )

        if event_info.type not in (EventType.GET, EventType.POST, EventType.STREAM):
            logger.warning(
                __name__,
                "Event type %s is not supported by job runner: %s",
                event_info.type,
                event_name,
            )
            raise NotImplementedError(f"Unsupported event type for job runner: {event_info.type}")

        raise NotImplementedError(f"Unsupported event type: {event_info.type}")

    except Exception as e:  # pylint: disable=broad-except
        logger.error(__name__, e)
        raise
    finally:
        if background_tasks:
            await _stop_background_tasks(background_tasks)
        await runtime.server.stop()


async def _wait_streams_ready(
    tasks: List[Tuple[AppEngine, str, asyncio.Task]],
    delay_auto_start_seconds: int,
) -> None:
    if not tasks:
        return
    timeout = max(1.0, float(delay_auto_start_seconds) + 2.0)
    loop = asyncio.get_event_loop()
    end_ts = loop.time() + timeout
    pending = {(app_engine, name) for app_engine, name, _ in tasks}
    while pending and loop.time() < end_ts:
        pending = {(ae, name) for ae, name, _ in tasks if not ae.is_running(name)}
        await asyncio.sleep(0.05)
    if pending:
        logger.warning(
            __name__,
            "Some stream events not running yet: %s",
            [name for _, name in pending],
        )


async def _stop_background_tasks(
    tasks: List[Tuple[AppEngine, str, asyncio.Task]],
) -> None:
    for app_engine, event_name, _ in tasks:
        if app_engine.is_running(event_name):
            await app_engine.stop_event(event_name)
    try:
        await asyncio.wait_for(
            asyncio.gather(*(task for _, _, task in tasks), return_exceptions=True),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        for _, _, task in tasks:
            task.cancel()


def _start_related_streams(
    *,
    app_engine: AppEngine,
    event_name: str,
    include_self: bool = True,
) -> List[Tuple[AppEngine, str, asyncio.Task]]:
    """
    Starts only stream events required to process the first stream output produced
    by the given event (including SHUFFLE/spawn first stage).
    """
    targets: List[Tuple[AppEngine, str]] = []
    base_event_name, _ = event_and_step(event_name)

    event_info = app_engine.effective_events[event_name]
    if include_self and event_info.type == EventType.STREAM:
        targets.append((app_engine, event_name))
    stream_names = [event_info.write_stream.name] if event_info.write_stream is not None else []
    if stream_names:
        logger.info(
            __name__,
            "Starting first-hop stream consumers for write_stream=%s",
            stream_names[0],
        )
    for evt_name, evt_info in app_engine.effective_events.items():
        evt_base, stage = event_and_step(evt_name)
        if (
            stage is not None
            and evt_base == base_event_name
            and evt_info.read_stream
            and evt_info.read_stream.name in stream_names
        ):
            if evt_info.type == EventType.SERVICE:
                logger.warning(
                    __name__,
                    "SERVICE event skipped while resolving SHUFFLE streams: %s",
                    evt_name,
                )
                continue
            targets.append((app_engine, evt_name))

    unique: List[Tuple[AppEngine, str]] = []
    seen_events = set()
    for app_engine, evt_name in targets:
        key = (app_engine.app_key, evt_name)
        if key not in seen_events:
            unique.append((app_engine, evt_name))
            seen_events.add(key)

    tasks: List[Tuple[AppEngine, str, asyncio.Task]] = []
    for app_engine, evt_name in unique:
        evt_info = app_engine.effective_events[evt_name]
        if evt_info.type == EventType.STREAM and evt_info.read_stream is not None:
            tasks.append(
                (
                    app_engine,
                    evt_name,
                    asyncio.create_task(app_engine.read_stream(event_name=evt_name)),
                )
            )
    return tasks


async def _execute_setup_event(
    app_engine: AppEngine,
    event_name: str,
    plugin_engine: Optional[AppEngine] = None,
) -> None:
    event_settings = get_event_settings(app_engine.settings, event_name)
    context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=app_engine.app_config if plugin_engine is None else plugin_engine.app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=_job_track_ids(app_engine.app_config, event_name),
        auth_info={},
    )
    logger.start(context)
    if plugin_engine is None:
        await app_engine.execute(context=context, query_args=None, payload=None)
    else:
        await plugin_engine.execute(context=context, query_args=None, payload=None)
    logger.done(context, extra=metrics(context))


async def _run_setup_events(
    app_engine: AppEngine,
    *,
    plugin_engine: Optional[AppEngine] = None,
    plug_mode: Optional[EventPlugMode] = None,
) -> None:
    engine = plugin_engine or app_engine
    for event_name, event_info in engine.effective_events.items():
        if event_info.type != EventType.SETUP:
            continue
        if plug_mode and event_info.plug_mode != plug_mode:
            continue
        await _execute_setup_event(app_engine, event_name, plugin_engine=plugin_engine)


def _job_track_ids(app_config: AppConfig, event_name: str) -> dict:
    now = datetime.now(tz=timezone.utc).isoformat()
    return {
        "track.operation_id": str(uuid.uuid4()),
        "track.request_id": str(uuid.uuid4()),
        "track.request_ts": now,
        "track.client_app_key": app_config.app_key(),
        "track.client_event_name": event_name,
    }


if __name__ == "__main__":
    sys_args = parse_args(sys.argv[1:])
    result = asyncio.run(
        run_job(
            config_files=sys_args.config_files,
            event_name=sys_args.event_name,
            payload=sys_args.payload,
            start_streams=sys_args.start_streams,
            max_events=sys_args.max_events,
        )
    )
    if result is not None:
        print(Payload.to_json(result))
