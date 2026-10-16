import asyncio
from collections.abc import AsyncGenerator
from copy import copy
from typing import Any, ClassVar

from hopeit.app.config import (
    AppConfig,
    Compression,
    EventDescriptor,
    Serialization,
    StreamQueue,
)
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import DataObject, EventPayload
from hopeit.server.engine import AppEngine, Server
from hopeit.server.events import EventHandler, get_runtime_settings
from hopeit.streams import StreamEvent, StreamManager, StreamOSError
from mock_app import MockData, MockResult  # type: ignore


class MockAppEngine(AppEngine):
    def __init__(
        self,
        *,
        app_config: AppConfig,
        plugins: list[AppConfig],
        enabled_groups: list[str],
        streams_wait_on_stop: bool = True,
    ):
        """
        Creates an instance of the AppEngine

        :param app_config: AppConfig, Hopeit application configuration as specified in config module
        """
        self.effective_events = self._config_effective_events(app_config, enabled_groups)
        self.app_config = app_config
        self.app_key = app_config.app_key()
        self.plugins = plugins
        self.settings = get_runtime_settings(app_config, plugins)
        self.streams_wait_on_stop = streams_wait_on_stop
        self.read_stream_calls: list[dict[str, Any]] = []

    async def start(self):
        self.stream_manager = MockStreamManager(address="mock")
        assert self.app_config.server is not None
        stream_config = self.app_config.server.streams

        await self.stream_manager.connect(stream_config)
        return self

    async def stop(self):
        await self.stream_manager.close()

    async def read_stream(
        self,
        *,
        event_name: str,
        max_events: int | None = None,
        stop_when_empty: bool = False,
        wait_start: bool = True,
        test_mode: bool = False,
    ) -> None:
        self.read_stream_calls.append(
            {
                "event_name": event_name,
                "max_events": max_events,
                "stop_when_empty": stop_when_empty,
                "wait_start": wait_start,
                "test_mode": test_mode,
            }
        )


class MockEventHandler(EventHandler):
    input_query_args: ClassVar[dict[str, Any]] = {"query_arg1": "ok"}
    input_payload = MockData("ok")
    expected_result = MockResult("ok: ok", processed=True)
    test_track_ids: ClassVar[dict[str, Any]] = {
        "track.operation_id": "test_operation_id",
        "track.request_id": "test_request_id",
        "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
        "track.session_id": "test_session_id",
    }
    expected_track_ids = test_track_ids
    call_function = None

    def __init__(
        self,
        *,
        app_config: AppConfig,
        plugins: list[AppConfig],
        effective_events: dict[str, EventDescriptor],
        settings: dict[str, Any],
    ):
        self.app_config = app_config
        self.plugins = plugins
        self.effective_events = effective_events
        self.settings = settings

    async def handle_async_event(
        self,
        *,
        context: EventContext,
        query_args: dict | None,
        payload: EventPayload | None,
    ) -> AsyncGenerator[EventPayload | None, None]:
        assert payload == MockEventHandler.input_payload
        if MockEventHandler.call_function is not None:
            yield MockEventHandler.call_function(payload, context)
        elif isinstance(payload, MockData) and payload.value == "fail":  # type: ignore
            raise ValueError("Test for error")
        elif isinstance(payload, MockData) and payload.value == "cancel":  # type: ignore
            raise asyncio.CancelledError("Test for cancellation")
        elif isinstance(payload, MockData) and payload.value == "timeout":  # type: ignore
            await asyncio.sleep(5.0)
        yield MockEventHandler.expected_result

    async def postprocess(
        self,
        *,
        context: EventContext,
        payload: EventPayload | None,
        response: PostprocessHook,
    ) -> EventPayload | None:
        response.set_header("PluginHeader", "PluginHeaderValue")
        response.set_cookie("PluginCookie", "PluginCookieValue")
        response.set_status(999)
        return payload


class MockStreamManager(StreamManager):
    test_queue = StreamQueue.AUTO
    test_payload = MockResult("ok: ok", processed=True)
    test_track_ids: ClassVar[dict[str, Any]] = {
        "track.request_id": "test_request_id",
        "track.request_ts": "2020-02-05T17:07:37.771396+00:00",
        "track.session_id": "test_session_id",
        "stream.consumer_group": "test_group",
        "stream.msg_id": "0000000000-0",
        "stream.name": "test_stream",
        "stream.event_id": "test_id",
        "stream.event_ts": "",
        "stream.read_ts": "2020-02-05T17:07:39.771396+00:00",
        "stream.submit_ts": "2020-02-05T17:07:38.771396+00:00",
    }
    test_auth_info: ClassVar[dict[str, Any]] = {"allowed": True, "auth_type": "Unsecured"}
    closed = True
    last_read_message = None
    error_pattern: ClassVar[list[Any]] = [None]

    last_write_stream_names: ClassVar[list[str]] = []
    last_write_queue_names: ClassVar[list[str]] = []

    last_read_stream_names: ClassVar[list[str]] = []
    last_read_queue_names: ClassVar[list[str]] = []

    def __init__(self, address: str):
        self.address = address
        self.write_stream_name: str | None = None
        self.write_stream_queue: str | None = None
        self.write_stream_payload: DataObject | None = None  # type: ignore
        self.write_track_ids: dict[str, str] | None = None
        self.write_auth_info: dict[str, Any] | None = None
        self.write_target_max_len: int | None = None
        self.write_count = 0

    async def connect(self, settings):
        MockStreamManager.closed = False
        return self

    async def close(self):
        MockStreamManager.closed = True

    async def write_stream(
        self,
        *,
        stream_name: str,
        queue: str,
        payload: EventPayload,
        track_ids: dict[str, str],
        auth_info: dict[str, Any],
        target_max_len: int = 0,
        compression: Compression,
        serialization: Serialization,
    ) -> int:
        if MockEventHandler.test_track_ids:
            track_ids["track.operation_id"] = MockEventHandler.test_track_ids["track.operation_id"]
            track_ids["track.request_ts"] = MockEventHandler.test_track_ids["track.request_ts"]
            track_ids["track.session_id"] = MockEventHandler.test_track_ids["track.session_id"]
            assert track_ids == MockEventHandler.test_track_ids
        self.write_stream_name = stream_name
        self.write_stream_queue = queue
        self.write_stream_payload = payload
        self.write_track_ids = track_ids
        self.write_auth_info = auth_info
        self.write_target_max_len = target_max_len
        self.write_count += 1
        self.last_write_stream_names.append(stream_name)
        self.last_write_queue_names.append(queue)
        return 1

    async def ensure_consumer_group(self, *, stream_name: str, consumer_group: str):
        pass

    async def ack_read_stream(
        self, *, stream_name: str, consumer_group: str, stream_event: StreamEvent
    ):
        return 1

    async def read_stream(
        self,
        *,
        stream_name: str,
        consumer_group: str,
        datatypes: dict[str, type],
        track_headers: list[str],
        offset: str,
        batch_size: int,
        timeout: int,
        batch_interval: int,
    ) -> list[StreamEvent | Exception]:
        if not MockStreamManager.closed:
            MockStreamManager.last_read_message = StreamEvent(
                msg_internal_id=b"0000000000-0",
                queue=MockStreamManager.test_queue or stream_name.split(".")[-1],
                payload=MockStreamManager.test_payload,
                track_ids=MockStreamManager.test_track_ids,
                auth_info=MockStreamManager.test_auth_info,
            )
            results: list[StreamEvent | Exception] = []
            for i, err_mode in enumerate(copy(MockStreamManager.error_pattern)):
                if err_mode is None:
                    results.append(MockStreamManager.last_read_message)
                    self.last_read_stream_names.append(stream_name)
                    self.last_read_queue_names.append(MockStreamManager.last_read_message.queue)
                    await asyncio.sleep(timeout)
                elif isinstance(err_mode, StreamOSError):
                    MockStreamManager.error_pattern = MockStreamManager.error_pattern[i + 1 :]
                    raise err_mode
                else:
                    results.append(err_mode)
            return results
        return []


class MockServer(Server):
    def __init__(self):
        self.app = None

    async def start(self):
        pass

    async def stop(self):
        pass

    async def start_app(self, app_config: AppConfig, enabled_groups: list[str]):
        self.app = MockAppEngine(app_config=app_config, plugins=[], enabled_groups=enabled_groups)

    def app_engine(self, *, app_key: str) -> AppEngine:
        return self.app
