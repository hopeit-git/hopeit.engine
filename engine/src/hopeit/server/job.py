"""
Job runner module to execute a single event without starting a web server.
"""

from collections import namedtuple
import argparse
import asyncio
import sys
from typing import List, Optional, Tuple, Type

from multidict import CIMultiDict, CIMultiDictProxy

from hopeit.app.config import AppConfig, EventDescriptor, EventSettings, EventType
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
    --start-streams: auto start reading stream and service events
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
    base_event, _ = event_and_step(event_name)
    matches = [config for config in app_configs if base_event in config.events]
    if len(matches) == 0:
        raise ValueError(f"Event not found: {event_name}")
    if len(matches) > 1:
        app_keys = ", ".join(config.app_key() for config in matches)
        raise ValueError(f"Event '{event_name}' found in multiple apps: {app_keys}")
    return matches[0]


def _start_configs_for_event(app_configs: List[AppConfig], event_name: str) -> List[AppConfig]:
    owner = _select_app_config(app_configs, event_name)
    configs_by_key = {config.app_key(): config for config in app_configs}
    ordered: List[AppConfig] = []
    seen = set()
    for plugin in owner.plugins:
        key = plugin.app_key()
        if key not in configs_by_key:
            raise ValueError(f"Missing plugin config for app_key={key}")
        if key not in seen:
            ordered.append(configs_by_key[key])
            seen.add(key)
    owner_key = owner.app_key()
    if owner_key not in seen:
        ordered.append(owner)
    return ordered


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
        track_ids={},
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
    """
    if len(config_files) < 2:
        raise ValueError("config_files must include server config and at least one app config")

    server_config = _load_engine_config(config_files[0])
    app_configs = [_load_app_config(path) for path in config_files[1:]]
    for config in app_configs:
        config.server = server_config
    start_configs = _start_configs_for_event(app_configs, event_name)

    await runtime.server.start(config=server_config)
    background_tasks: List[Tuple[AppEngine, str, asyncio.Task]] = []
    try:
        owner_config = start_configs[-1]
        plugin_configs = start_configs[:-1]
        logger.info(__name__, f"Starting app={owner_config.app_key()}...")
        app_engine = await AppEngine(
            app_config=owner_config,
            plugins=plugin_configs,
            enabled_groups=[],
            stop_wait_on_streams=False,
        ).start(init_auth=False)
        runtime.server.app_engines[owner_config.app_key()] = app_engine
        event_info = app_engine.effective_events[event_name]

        if event_info.type in (EventType.STREAM, EventType.SERVICE):
            if event_info.type == EventType.STREAM:
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
            return await app_engine.service_loop(event_name=event_name)

        if start_streams or _has_shuffle_stages(app_engine, event_name):
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
            "Some stream/service events not running yet: %s",
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
) -> List[Tuple[AppEngine, str, asyncio.Task]]:
    """
    Starts only stream/service events required to process the given event output,
    following stream chains (including SHUFFLE/spawn stages).
    """
    targets: List[Tuple[AppEngine, str]] = []
    pending_streams: List[str] = []
    seen_streams = set()

    event_info = app_engine.effective_events[event_name]
    if event_info.type in (EventType.STREAM, EventType.SERVICE):
        targets.append((app_engine, event_name))
    if event_info.write_stream is not None:
        pending_streams.append(event_info.write_stream.name)

    while pending_streams:
        stream_name = pending_streams.pop(0)
        if stream_name in seen_streams:
            continue
        seen_streams.add(stream_name)
        for evt_name, evt_info in app_engine.effective_events.items():
            if evt_info.read_stream and evt_info.read_stream.name == stream_name:
                targets.append((app_engine, evt_name))
                if evt_info.write_stream is not None:
                    pending_streams.append(evt_info.write_stream.name)

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
        elif evt_info.type == EventType.SERVICE:
            tasks.append(
                (
                    app_engine,
                    evt_name,
                    asyncio.create_task(app_engine.service_loop(event_name=evt_name)),
                )
            )
    return tasks


def _has_shuffle_stages(app_engine: AppEngine, event_name: str) -> bool:
    for evt_name in app_engine.effective_events.keys():
        base_event, stage = event_and_step(evt_name)
        if base_event == event_name and stage is not None:
            return True
    return False


if __name__ == "__main__":
    sys_args = parse_args(sys.argv[1:])
    asyncio.run(
        run_job(
            config_files=sys_args.config_files,
            event_name=sys_args.event_name,
            payload=sys_args.payload,
            start_streams=sys_args.start_streams,
            max_events=sys_args.max_events,
        )
    )
