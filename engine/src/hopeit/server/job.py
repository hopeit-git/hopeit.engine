"""
Job runner module to execute a single event without starting a web server.
"""

from collections import namedtuple
import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Type

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
from hopeit.server.logger import engine_logger, extra_logger
from hopeit.server.metrics import metrics
from hopeit.server.steps import event_and_step, find_datatype_handler

__all__ = ["parse_args", "parse_track_ids", "parse_query_args", "resolve_payload", "run_job"]

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
        "query_args",
    ],
)


def _read_payload_source(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    with open(source, "r", encoding="utf-8") as f:
        return f.read()


def resolve_payload(payload: Optional[str]) -> Optional[str]:
    """
    Returns payload string, optionally reading content from file.
    Supports curl syntax with @file or @- for stdin.
    """
    if payload and payload.startswith("@"):
        source = payload[1:]
        if not source:
            raise ValueError("Payload file path missing after '@'.")
        return _read_payload_source(source)
    return payload


def _parse_json_kv_payload(payload: Optional[str], name: str) -> Dict[str, str]:
    if payload is None:
        return {}
    if not payload.strip():
        raise ValueError(f"{name} payload is empty.")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid {name} JSON payload: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"{name} payload must be a JSON object.")
    parsed: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{name} key cannot be empty.")
        if value is None:
            parsed[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            parsed[key] = str(value)
        else:
            raise ValueError(
                f"{name} value for key '{key}' must be a scalar (string, number, boolean, null)."
            )
    return parsed


def parse_track_ids(track_payload: Optional[str]) -> Dict[str, str]:
    """
    Parse --track JSON object into a dict, normalizing keys to 'track.*'.
    """
    track_ids = _parse_json_kv_payload(track_payload, "track")
    normalized: Dict[str, str] = {}
    for key, value in track_ids.items():
        if not key.startswith("track."):
            key = f"track.{key}"
        normalized[key] = value
    return normalized


def parse_query_args(query_payload: Optional[str]) -> Dict[str, str]:
    """
    Parse --query-args JSON object into a dict.
    """
    return _parse_json_kv_payload(query_payload, "query-args")


def parse_args(args) -> ParsedArgs:
    """
    Parse command line arguments:
    --config-files: comma-separated list of server, plugins and app config files
    --event-name: event name to execute
    --payload: json string payload, optionally use @file or @- for stdin
    --start-streams: enable STREAM consumption
    --max-events: limit number of consumed events for STREAM runs
    --track: JSON object with track ids (use @file or @- for stdin)
    --query-args: JSON object with query args (use @file or @- for stdin)
    """
    parser = argparse.ArgumentParser(description="hopeit job runner")
    parser.add_argument("--config-files", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--payload")
    parser.add_argument("--start-streams", action="store_true")
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--track")
    parser.add_argument("--query-args", dest="query_args")

    parsed_args = parser.parse_args(args=args)
    payload = resolve_payload(parsed_args.payload)

    track_payload = resolve_payload(parsed_args.track)
    query_payload = resolve_payload(parsed_args.query_args)

    return ParsedArgs(
        config_files=parsed_args.config_files.split(","),
        event_name=parsed_args.event_name,
        payload=payload,
        start_streams=bool(parsed_args.start_streams),
        max_events=parsed_args.max_events,
        track_ids=parse_track_ids(track_payload),
        query_args=parse_query_args(query_payload),
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
    query_args: Optional[Dict[str, Any]] = None,
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
            query_args=query_args,
            payload=parsed_payload,
            request=preprocess_hook,
        )
        if (preprocess_hook.status is None) or (preprocess_hook.status == 200):
            result = await app_engine.execute(
                context=context, query_args=query_args, payload=result
            )
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
    track_ids: Optional[Dict[str, str]] = None,
    query_args: Optional[Dict[str, Any]] = None,
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
                streams_wait_on_stop=False,
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
            return await _execute_event(
                app_engine=app_engine,
                event_name=event_name,
                event_info=event_info,
                payload=payload,
                track_ids=track_ids,
                query_args=query_args,
            )

        elif event_info.type == EventType.STREAM:
            if payload is not None:
                return await _execute_event(
                    app_engine=app_engine,
                    event_name=event_name,
                    event_info=event_info,
                    payload=payload,
                    track_ids=track_ids,
                )
            else:
                if not start_streams:
                    logger.warning(
                        __name__,
                        "STREAM events require --start-streams: %s",
                        event_name,
                    )
                    raise NotImplementedError(
                        f"STREAM events require --start-streams: {event_name}"
                    )
                logger.info(
                    __name__,
                    "Consuming stream (job)...",
                    extra=extra(
                        prefix="stream.", app_key=app_engine.app_key, event_name=event_name
                    ),
                )
                await app_engine.read_stream(
                    event_name=event_name,
                    max_events=max_events,
                    stop_when_empty=True,
                    wait_start=False,
                )
                return None

        else:
            logger.warning(
                __name__,
                "Event type %s is not supported by job runner: %s",
                event_info.type,
                event_name,
            )
            raise NotImplementedError(f"Unsupported event type for job runner: {event_info.type}")

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
            query_args=sys_args.query_args,
        )
    )
    if result is not None:
        print(Payload.to_json(result))
