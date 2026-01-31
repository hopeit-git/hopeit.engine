import asyncio
from copy import copy
from typing import Optional, AsyncGenerator, Dict, List, Any, Union

from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import DataObject, EventPayload
from hopeit.server.events import EventHandler
from hopeit.server.engine import Server
from hopeit.streams import StreamManager, StreamEvent, StreamOSError
from hopeit.app.config import (
    AppConfig,
    EventDescriptor,
    Serialization,
    Compression,
    StreamQueue,
)
from hopeit.server.engine import AppEngine

from mock_app import MockData, MockResult  # type: ignore


class MockAppEngine(AppEngine):
    def __init__(
        self,
        *,
        app_config: AppConfig,
        plugins: List[AppConfig],
        enabled_groups: List[str],
        init_auth: bool = True,
    ):
        """
        Creates an instance of the AppEngine

        :param app_config: AppConfig, Hopeit application configuration as specified in config module
        """
        self.effective_events = self._config_effective_events(app_config, enabled_groups)
        self.app_config = app_config
        self.plugins = plugins
        self.init_auth = init_auth

    async def start(self):
        self.stream_manager = MockStreamManager(address="mock")
        assert self.app_config.server is not None
        stream_config = self.app_config.server.streams

        await self.stream_manager.connect(stream_config)
        return self

    async def stop(self):
        await self.stream_manager.close()


class MockEventHandler(EventHandler):
    input_query_args = {"query_arg1": "ok"}
    input_payload = MockData("ok")
    expected_result = MockResult("ok: ok", processed=True)
    test_track_ids = {
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
        plugins: List[AppConfig],
        effective_events: Dict[str, EventDescriptor],
        settings: Dict[str, Any],
    ):
        self.app_config = app_config
        self.plugins = plugins
        self.effective_events = effective_events
        self.settings = settings

    async def handle_async_event(
        self,
        *,
        context: EventContext,
        query_args: Optional[dict],
        payload: Optional[EventPayload],
    ) -> AsyncGenerator[Optional[EventPayload], None]:
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
        payload: Optional[EventPayload],
        response: PostprocessHook,
    ) -> Optional[EventPayload]:
        response.set_header("PluginHeader", "PluginHeaderValue")
        response.set_cookie("PluginCookie", "PluginCookieValue")
        response.set_status(999)
        return payload


class MockStreamManager(StreamManager):
    test_queue = StreamQueue.AUTO
    test_payload = MockResult("ok: ok", processed=True)
    test_track_ids = {
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
    test_auth_info = {"allowed": True, "auth_type": "Unsecured"}
    closed = True
    last_read_message = None
    error_pattern = [None]

    last_write_stream_names: List[str] = []
    last_write_queue_names: List[str] = []

    last_read_stream_names: List[str] = []
    last_read_queue_names: List[str] = []

    def __init__(self, address: str):
        self.address = address
        self.write_stream_name: Optional[str] = None
        self.write_stream_queue: Optional[str] = None
        self.write_stream_payload: Optional[DataObject] = None  # type: ignore
        self.write_track_ids: Optional[Dict[str, str]] = None
        self.write_auth_info: Optional[Dict[str, Any]] = None
        self.write_target_max_len: Optional[int] = None
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
        track_ids: Dict[str, str],
        auth_info: Dict[str, Any],
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
        datatypes: Dict[str, type],
        track_headers: List[str],
        offset: str,
        batch_size: int,
        timeout: int,
        batch_interval: int,
    ) -> List[Union[StreamEvent, Exception]]:
        if not MockStreamManager.closed:
            MockStreamManager.last_read_message = StreamEvent(
                msg_internal_id=b"0000000000-0",
                queue=MockStreamManager.test_queue or stream_name.split(".")[-1],
                payload=MockStreamManager.test_payload,
                track_ids=MockStreamManager.test_track_ids,
                auth_info=MockStreamManager.test_auth_info,
            )
            results: List[Union[StreamEvent, Exception]] = []
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

    async def start_app(
        self,
        app_config: AppConfig,
        enabled_groups: List[str],
        init_auth: bool = True,
    ):
        self.app = MockAppEngine(
            app_config=app_config,
            plugins=[],
            enabled_groups=enabled_groups,
        )

    def app_engine(self, *, app_key: str) -> AppEngine:
        return self.app
