import pytest
import asyncio

from hopeit.app.context import EventContext
from hopeit.server.collector import Collector, AsyncCollector
from hopeit.server.events import get_event_settings

from mock_app import mock_app_config  # type: ignore


async def test_async_collector(mock_app_config):
    settings = get_event_settings(mock_app_config.effective_settings, "mock_event")
    context = EventContext(
        app_config=mock_app_config,
        plugin_config=mock_app_config,
        event_name="mock_event",
        settings=settings,
        track_ids={},
        auth_info={},
    )

    collector = (
        await AsyncCollector()
        .input("0")
        .steps(("step1", step1), ("step2", step2), ("step3", step3))
        .run(context)
    )
    result = await collector["step3"]
    assert result == "((0+mock_event+step1)&(0+mock_event+step2)+mock_event+step3)"


async def step1(collector: Collector, context: EventContext) -> str:
    payload = await collector["payload"]
    await asyncio.sleep(0.01)
    return f"({payload}+{context.event_name}+step1)"


async def step2(collector: Collector, context: EventContext) -> str:
    payload = await collector["payload"]
    await asyncio.sleep(0.01)
    return f"({payload}+{context.event_name}+step2)"


async def step3(collector: Collector, context: EventContext) -> str:
    step1 = await collector["step1"]
    step2 = await collector["step2"]
    await asyncio.sleep(0.01)
    return f"({step1}&{step2}+{context.event_name}+step3)"
