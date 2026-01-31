"""
Job runner module to execute a single event without starting a web server.
"""

from collections import namedtuple
import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Type

from multidict import CIMultiDict, CIMultiDictProxy

from hopeit.app.config import (
    AppConfig,
    EventDescriptor,
    EventPlugMode,
    EventSettings,
    StreamQueue,
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
from hopeit.server.logger import engine_logger, extra_logger
from hopeit.server.metrics import metrics
from hopeit.server.steps import event_and_step, find_datatype_handler

__all__ = ["parse_args", "parse_track_ids", "resolve_payload", "run_job"]

logger = engine_logger()
extra = extra_logger()

ParsedArgs = namedtuple(
    "ParsedArgs",
    [
        "config_files",
        "event_name",
        "payload",
        "start_streams",
        "max_events",
        "track_ids",
        "in_process_shuffle",
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


def parse_track_ids(track_items: Optional[List[str]]) -> Dict[str, str]:
    """
    Parse --track key=value pairs into a dict, normalizing keys to 'track.*'.
    """
    track_ids: Dict[str, str] = {}
    if not track_items:
        return track_ids
    for item in track_items:
        if "=" not in item:
            raise ValueError(f"Invalid track format '{item}', expected key=value.")
        raw_key, value = item.split("=", 1)
        key = raw_key.strip()
        if not key:
            raise ValueError("Track key cannot be empty.")
        if not key.startswith("track."):
            key = f"track.{key}"
        track_ids[key] = value
    return track_ids


def parse_args(args) -> ParsedArgs:
    """
    Parse command line arguments:
    --config-files: comma-separated list of server, plugins and app config files
    --event-name: event name to execute
    --payload: json string payload, optionally use @file or @- for stdin
    --input-file: read payload from file (same as --payload=@file)
    --start-streams: enable STREAM consumption
    --max-events: limit number of consumed events for STREAM runs
    --track: extra track ids (repeatable), format key=value (key can omit 'track.' prefix)
    --in-process-shuffle: execute SHUFFLE stages in-process (no stream consumers)
    """
    parser = argparse.ArgumentParser(description="hopeit job runner")
    parser.add_argument("--config-files", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--payload")
    parser.add_argument("--input-file")
    parser.add_argument("--start-streams", action="store_true")
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--track", action="append", default=[])
    parser.add_argument("--in-process-shuffle", action="store_true")

    parsed_args = parser.parse_args(args=args)
    payload = resolve_payload(parsed_args.payload, parsed_args.input_file)

    return ParsedArgs(
        config_files=parsed_args.config_files.split(","),
        event_name=parsed_args.event_name,
        payload=payload,
        start_streams=bool(parsed_args.start_streams),
        max_events=parsed_args.max_events,
        track_ids=parse_track_ids(parsed_args.track),
        in_process_shuffle=bool(parsed_args.in_process_shuffle),
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
    track_ids: Optional[Dict[str, str]] = None,
) -> EventContext:
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=_job_track_ids(app_config, event_name, track_ids),
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
    track_ids: Optional[Dict[str, str]] = None,
) -> Optional[EventPayload]:
    event_settings = get_event_settings(app_engine.settings, event_name)
    context = _create_context(
        app_config=app_engine.app_config,
        event_name=event_name,
        event_settings=event_settings,
        track_ids=track_ids,
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


def _shuffle_stage_event_names(app_engine: AppEngine, event_name: str) -> List[str]:
    base_event, _ = event_and_step(event_name)
    stage_events: List[str] = []
    for evt_name in app_engine.effective_events.keys():
        evt_base, stage = event_and_step(evt_name)
        if evt_base != base_event:
            continue
        if evt_name != base_event and stage is None:
            continue
        stage_events.append(evt_name)
    return stage_events


async def _execute_shuffle_in_process(
    *,
    app_engine: AppEngine,
    event_name: str,
    event_info: EventDescriptor,
    payload: Optional[str],
    track_ids: Optional[Dict[str, str]],
    stage_events: List[str],
) -> Optional[EventPayload]:
    event_settings = get_event_settings(app_engine.settings, event_name)
    context = _create_context(
        app_config=app_engine.app_config,
        event_name=event_name,
        event_settings=event_settings,
        track_ids=track_ids,
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
        result_payload = await app_engine.preprocess(
            context=context,
            query_args=None,
            payload=parsed_payload,
            request=preprocess_hook,
        )
        if (preprocess_hook.status is not None) and (preprocess_hook.status != 200):
            logger.done(context, extra=metrics(context))
            return None

        assert app_engine.event_handler, "event_handler not created. Call `start()`."

        last_output: Optional[EventPayload] = None
        stage0_last_output: Optional[EventPayload] = None

        async def run_stage(stage_index: int, stage_payload: Optional[EventPayload]) -> None:
            nonlocal last_output
            nonlocal stage0_last_output
            stage_name = stage_events[stage_index]
            stage_settings = get_event_settings(app_engine.settings, stage_name)
            stage_context = _create_context(
                app_config=app_engine.app_config,
                event_name=stage_name,
                event_settings=stage_settings,
                track_ids=track_ids,
            )
            stage_event_info = app_engine.effective_events[stage_name]
            if stage_index == len(stage_events) - 1:
                batch: List[EventPayload] = []
                assert app_engine.event_handler
                async for output in app_engine.event_handler.handle_async_event(
                    context=stage_context,
                    query_args=None,
                    payload=stage_payload,
                ):
                    if output is None:
                        continue
                    last_output = output
                    if stage_event_info.write_stream is not None:
                        assert app_engine.stream_manager, (
                            "stream_manager not initialized. Call `start()`."
                        )
                        batch.append(output)
                        if len(batch) >= stage_settings.stream.batch_size:
                            await app_engine._write_stream_batch(  # pylint: disable=protected-access
                                batch=batch,
                                context=stage_context,
                                event_info=stage_event_info,
                                queue=StreamQueue.AUTO,
                            )
                            batch.clear()
                if stage_event_info.write_stream is not None and batch:
                    await app_engine._write_stream_batch(  # pylint: disable=protected-access
                        batch=batch,
                        context=stage_context,
                        event_info=stage_event_info,
                        queue=StreamQueue.AUTO,
                    )
                return
            assert app_engine.event_handler
            async for output in app_engine.event_handler.handle_async_event(
                context=stage_context,
                query_args=None,
                payload=stage_payload,
            ):
                if output is None:
                    continue
                last_output = output
                if stage_index == 0:
                    stage0_last_output = output
                await run_stage(stage_index + 1, output)

        await run_stage(0, result_payload)
        result = await app_engine.postprocess(
            context=context,
            payload=stage0_last_output,
            response=PostprocessHook(),
        )
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
    track_ids: Optional[Dict[str, str]] = None,
    in_process_shuffle: bool = False,
) -> Optional[EventPayload]:
    """
    Starts engine and apps from config files and executes a single event.

    Only GET, POST and STREAM events are supported.
    """
    if len(config_files) < 2:
        raise ValueError("config_files must include server config and at least one app config")

    server_config = _load_engine_config(config_files[0])
    app_configs = [_load_app_config(path) for path in config_files[1:]]
    track_ids = track_ids or {}
    for config in app_configs:
        config.server = server_config
        if track_ids:
            for key in track_ids:
                if key not in config.engine.track_headers:
                    config.engine.track_headers.append(key)
    owner_config = _select_app_config(app_configs, event_name)

    await runtime.server.start(config=server_config)
    try:
        for config in app_configs:
            logger.info(__name__, f"Starting app={config.app_key()}...")
            app_engine = await AppEngine(
                app_config=config,
                plugins=_plugins_for_app(config, app_configs),
                enabled_groups=[],
                stop_wait_on_streams=False,
                init_auth=False,
            ).start()
            runtime.server.app_engines[config.app_key()] = app_engine

        app_engine = runtime.server.app_engines[owner_config.app_key()]
        await _run_setup_events(app_engine, track_ids=track_ids)
        for plugin in owner_config.plugins:
            plugin_engine = runtime.server.app_engines[plugin.app_key()]
            await _run_setup_events(
                app_engine,
                plugin_engine=plugin_engine,
                plug_mode=EventPlugMode.ON_APP,
                track_ids=track_ids,
            )
        event_info = app_engine.effective_events[event_name]

        if event_info.type in (EventType.GET, EventType.POST):
            if in_process_shuffle:
                stage_events = _shuffle_stage_event_names(app_engine, event_name)
                if len(stage_events) > 1:
                    return await _execute_shuffle_in_process(
                        app_engine=app_engine,
                        event_name=event_name,
                        event_info=event_info,
                        payload=payload,
                        track_ids=track_ids,
                        stage_events=stage_events,
                    )
            return await _execute_event(
                app_engine=app_engine,
                event_name=event_name,
                event_info=event_info,
                payload=payload,
                track_ids=track_ids,
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
                    track_ids=track_ids,
                )
            if payload is not None:
                logger.warning(
                    __name__,
                    "STREAM events consume from streams; payload was provided and will be ignored.",
                )
                return None
            if not start_streams:
                logger.warning(
                    __name__,
                    "STREAM events require --start-streams: %s",
                    event_name,
                )
                raise NotImplementedError(f"STREAM events require --start-streams: {event_name}")
            logger.info(
                __name__,
                "Consuming stream (job)...",
                extra=extra(prefix="stream.", app_key=app_engine.app_key, event_name=event_name),
            )
            return await app_engine.read_stream(
                event_name=event_name,
                max_events=max_events,
                stop_when_empty=True,
                wait_start=False,
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
        await runtime.server.stop()


async def _execute_setup_event(
    app_engine: AppEngine,
    event_name: str,
    plugin_engine: Optional[AppEngine] = None,
    track_ids: Optional[Dict[str, str]] = None,
) -> None:
    event_settings = get_event_settings(app_engine.settings, event_name)
    context = EventContext(
        app_config=app_engine.app_config,
        plugin_config=app_engine.app_config if plugin_engine is None else plugin_engine.app_config,
        event_name=event_name,
        settings=event_settings,
        track_ids=_job_track_ids(app_engine.app_config, event_name, track_ids),
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
    track_ids: Optional[Dict[str, str]] = None,
) -> None:
    engine = plugin_engine or app_engine
    for event_name, event_info in engine.effective_events.items():
        if event_info.type != EventType.SETUP:
            continue
        if plug_mode and event_info.plug_mode != plug_mode:
            continue
        await _execute_setup_event(
            app_engine,
            event_name,
            plugin_engine=plugin_engine,
            track_ids=track_ids,
        )


def _job_track_ids(
    app_config: AppConfig,
    event_name: str,
    extra_track_ids: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    now = datetime.now(tz=timezone.utc).isoformat()
    track_ids = {
        "track.operation_id": str(uuid.uuid4()),
        "track.request_id": str(uuid.uuid4()),
        "track.request_ts": now,
        "track.client_app_key": app_config.app_key(),
        "track.client_event_name": event_name,
    }
    if extra_track_ids:
        track_ids.update(extra_track_ids)
    return track_ids


if __name__ == "__main__":
    sys_args = parse_args(sys.argv[1:])
    result = asyncio.run(
        run_job(
            config_files=sys_args.config_files,
            event_name=sys_args.event_name,
            payload=sys_args.payload,
            start_streams=sys_args.start_streams,
            max_events=sys_args.max_events,
            track_ids=sys_args.track_ids,
            in_process_shuffle=sys_args.in_process_shuffle,
        )
    )
    if result is not None:
        print(Payload.to_json(result))
