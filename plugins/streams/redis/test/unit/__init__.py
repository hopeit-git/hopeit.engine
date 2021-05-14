from typing import AsyncGenerator, Dict, List, Optional
import asyncio

from hopeit.dataobjects import EventPayload, dataobject, dataclass
from hopeit.app.config import AppConfig, EventDescriptor
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.server.events import EventHandler


@dataobject(event_id='value')
@dataclass
class MockData:
    """MockData object"""
    value: str


@dataobject(event_id='value')
@dataclass
class MockResult:
    value: str
    processed: bool = True


class MockEventHandler(EventHandler):
    input_query_args = {"query_arg1": "ok"}
    input_payload = MockData("ok")
    expected_result = MockResult("ok: ok", processed=True)
    test_track_ids = {
        'track.operation_id': 'test_operation_id',
        'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00',
        'track.session_id': 'test_session_id'
    }
    expected_track_ids = test_track_ids

    def __init__(self, *,
                 app_config: AppConfig,
                 plugins: List[AppConfig],
                 effective_events: Dict[str, EventDescriptor]):
        self.app_config = app_config
        self.plugins = plugins
        self.effective_events = effective_events

    async def handle_async_event(self, *,
                                 context: EventContext,
                                 query_args: Optional[dict],
                                 payload: Optional[EventPayload]) -> AsyncGenerator[Optional[EventPayload], None]:
        assert payload == MockEventHandler.input_payload
        assert all(x in context.track_ids.keys() for x in self.app_config.engine.track_headers)
        if isinstance(payload, MockData) and payload.value == 'fail':  # type: ignore
            raise ValueError("Test for error")
        if isinstance(payload, MockData) and payload.value == 'timeout':  # type: ignore
            await asyncio.sleep(5.0)
        yield MockEventHandler.expected_result

    async def postprocess(self, *,
                          context: EventContext,
                          payload: Optional[EventPayload],
                          response: PostprocessHook) -> Optional[EventPayload]:
        response.set_header("PluginHeader", "PluginHeaderValue")
        response.set_cookie("PluginCookie", "PluginCookieValue")
        response.set_status(999)
        return payload


class TestStreamData:
    test_queue = 'DEFAULT'
    test_payload = MockResult("ok: ok", processed=True)
    test_track_ids = {
        'track.request_id': 'test_request_id',
        'track.request_ts': '2020-02-05T17:07:37.771396+00:00',
        'track.session_id': 'test_session_id',
        'stream.consumer_group': 'test_group',
        'stream.msg_id': '0000000000-0',
        'stream.name': 'test_stream',
        'stream.event_id': 'test_id',
        'stream.event_ts': '',
        'stream.read_ts': '2020-02-05T17:07:39.771396+00:00',
        'stream.submit_ts': '2020-02-05T17:07:38.771396+00:00'
    }
    test_auth_info = {
        'allowed': True,
        'auth_type': 'Unsecured'
    }
