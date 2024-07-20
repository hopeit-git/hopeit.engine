from datetime import datetime, timezone
from typing import List, Union

import pytest

from hopeit.dataobjects import dataclass, dataobject
from hopeit.streams import (
    StreamCircuitBreaker,
    StreamEvent,
    StreamManager,
    StreamOSError,
)


@dataobject(event_id="value", event_ts="ts")
@dataclass
class MockData:
    value: str
    ts: datetime


@dataclass
class MockInvalidDataEvent:
    value: str


class MockStreamManager(StreamManager):
    def __init__(self) -> None:
        self.connected = True

    async def ensure_consumer_group(self, **kwargs) -> None:
        if self.connected:
            return
        else:
            raise StreamOSError()

    async def read_stream(self, **kwargs) -> List[Union[StreamEvent, Exception]]:
        if self.connected:
            return [
                StreamEvent(
                    b"test1",
                    "test-queue",
                    payload=MockData(value="mock1", ts=datetime(2020, 1, 1)),
                    track_ids={},
                    auth_info={},
                ),
                StreamEvent(
                    b"test1",
                    "test-queue",
                    payload=MockData(value="mock2", ts=datetime(2020, 1, 1)),
                    track_ids={},
                    auth_info={},
                ),
            ]
        else:
            raise StreamOSError()

    async def write_stream(self, **kwargs) -> int:
        if self.connected:
            return 1
        else:
            raise StreamOSError()


def test_as_data_event():
    test_data = MockData("ok", datetime.now(tz=timezone.utc))
    assert StreamManager.as_data_event(test_data) == test_data
    with pytest.raises(NotImplementedError):
        StreamManager.as_data_event(MockInvalidDataEvent("ok"))


@pytest.mark.asyncio
async def test_stream_circuit_breaker_ensure_consumer_group():
    stream_manager = MockStreamManager()
    stream_manager.connected = True

    circuit_breaker = StreamCircuitBreaker(
        stream_manager=stream_manager,
        initial_backoff_seconds=0.1,
        num_failures_open_circuit_breaker=2,
        max_backoff_seconds=0.4,
    )

    async def check_result(state: int, backoff: int):
        await circuit_breaker.ensure_consumer_group()
        assert circuit_breaker.state == state
        assert circuit_breaker.backoff == backoff

    async def check_exception(state: int, backoff: int):
        with pytest.raises(StreamOSError):
            await circuit_breaker.ensure_consumer_group()
        assert circuit_breaker.state == state
        assert circuit_breaker.backoff == backoff

    # circuit breakes is closed (0)
    await check_result(state=0, backoff=0.0)

    # error condition, semi-open (1)
    stream_manager.connected = False
    await check_exception(state=1, backoff=0.1)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.1)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.2)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.4)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.4)

    # recover connection
    stream_manager.connected = True
    await check_result(state=1, backoff=0.1)

    # error again
    stream_manager.connected = False
    await check_exception(state=2, backoff=0.1)

    # recover connection
    stream_manager.connected = True
    await check_result(state=1, backoff=0.1)

    # recover fully
    await check_result(state=0, backoff=0.0)


@pytest.mark.asyncio
async def test_stream_circuit_breaker_read_stream():
    stream_manager = MockStreamManager()
    stream_manager.connected = True

    circuit_breaker = StreamCircuitBreaker(
        stream_manager=stream_manager,
        initial_backoff_seconds=0.1,
        num_failures_open_circuit_breaker=2,
        max_backoff_seconds=0.4,
    )

    async def check_result(state: int, backoff: int):
        res = await circuit_breaker.read_stream()
        assert len(res) == 2
        assert circuit_breaker.state == state
        assert circuit_breaker.backoff == backoff

    async def check_exception(state: int, backoff: int):
        res = await circuit_breaker.read_stream()
        assert len(res) == 1
        assert isinstance(res[0], StreamOSError)
        assert circuit_breaker.state == state
        assert circuit_breaker.backoff == backoff

    # circuit breakes is closed (0)
    await check_result(state=0, backoff=0.0)

    # error condition, semi-open (1)
    stream_manager.connected = False
    await check_exception(state=1, backoff=0.1)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.1)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.2)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.4)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.4)

    # recover connection
    stream_manager.connected = True
    await check_result(state=1, backoff=0.1)

    # error again
    stream_manager.connected = False
    await check_exception(state=2, backoff=0.1)

    # recover connection
    stream_manager.connected = True
    await check_result(state=1, backoff=0.1)

    # recover fully
    await check_result(state=0, backoff=0.0)


@pytest.mark.asyncio
async def test_stream_circuit_breaker_write_stream():
    stream_manager = MockStreamManager()
    stream_manager.connected = True

    circuit_breaker = StreamCircuitBreaker(
        stream_manager=stream_manager,
        initial_backoff_seconds=0.1,
        num_failures_open_circuit_breaker=2,
        max_backoff_seconds=0.4,
    )

    async def check_result(state: int, backoff: float):
        res = await circuit_breaker.write_stream()
        assert res == 1
        assert circuit_breaker.state == state
        assert circuit_breaker.backoff == backoff

    async def check_exception(state: int, backoff: float):
        with pytest.raises(StreamOSError):
            await circuit_breaker.write_stream()
        assert circuit_breaker.state == state
        assert circuit_breaker.backoff == backoff

    # circuit breakes is closed (0)
    await check_result(state=0, backoff=0.0)

    # error condition, semi-open (1)
    stream_manager.connected = False
    await check_exception(state=1, backoff=0.1)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.1)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.2)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.4)

    # error repeats, open (2)
    await check_exception(state=2, backoff=0.4)

    # recover connection
    stream_manager.connected = True
    await check_result(state=1, backoff=0.1)

    # error again
    stream_manager.connected = False
    await check_exception(state=2, backoff=0.1)

    # recover connection
    stream_manager.connected = True
    await check_result(state=1, backoff=0.1)

    # recover fully
    await check_result(state=0, backoff=0.0)
