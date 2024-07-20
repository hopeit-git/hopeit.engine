import asyncio

from hopeit.app.events import collector_step
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from hopeit.server.collector import Collector
from . import MockData, MockResult

__steps__ = [
    collector_step(payload=MockData).gather("step1", "step2", "step3"),
    "result",
]

logger, extra = app_extra_logger()


async def step1(collector: Collector, context: EventContext) -> str:
    payload = await collector["payload"]
    await asyncio.sleep(0.01)
    return f"({payload.value}+{context.event_name}+step1)"


async def step2(collector: Collector, context: EventContext) -> str:
    payload = await collector["payload"]
    await asyncio.sleep(0.01)
    return f"({payload.value}+{context.event_name}+step2)"


async def step3(collector: Collector, context: EventContext) -> MockResult:
    step1 = await collector["step1"]
    step2 = await collector["step2"]
    await asyncio.sleep(0.01)
    return MockResult(f"({step1}&{step2}+{context.event_name}+step3)")


async def result(collector: Collector, context: EventContext) -> MockResult:
    return await collector["step3"]
