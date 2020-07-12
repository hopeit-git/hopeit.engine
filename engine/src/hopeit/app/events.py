"""
Events handling
"""
from typing import AsyncGenerator, TypeVar, Type

__all__ = ['Spawn', 'SHUFFLE', 'collector_step', 'Collector']

from hopeit.dataobjects import EventPayloadType
from hopeit.server.steps import CollectorStepsDescriptor, SHUFFLE
from hopeit.server.collector import Collector

T = TypeVar('T')
Spawn = AsyncGenerator[T, None]


def collector_step(*, payload: Type[EventPayloadType]) -> CollectorStepsDescriptor:
    """
    Specifies a set of steps that would be run using `AsyncCollector` implementation. AsyncCollector ensures
    all steps are run as concurrently as possible using `asyncio.gather(...)` mechanism.
    Each step has to implement the signature: `step(collector: Collector, context: EventContext)`
    and the data returned by the step will be put in the collector.
    Each step should await for data in the collector using `data = await collector['step_name']`.
    This way collector guarantees that dependant steps will be executed before steps
    using generated data in the collector.

    :param payload: EventPayloadType, collector contains a special bucket for "payload" information
        that will be submitted on evey call and can be accessed using `payload = await collector['payload']`,
        so Type of payload needs to be informed to create the appropriate handler: collector(payload=DataType)

    Example:

    Use inline in __steps__ definition of event implementation,
    to run step1, step2 and step3 concurrently using a Collector, and then
    seq_step4, and seq_step5 sequentially::

        __steps__ = [
            collector_step(payload=InputType).gather('step1', 'step2', 'step3),
            'seq_step4', 'seq_step5')
        ]

        async def step1(collector: Collector, context: EventContext) -> StepData:
            payload = await collector['payload']
            # do something with payload, this can run concurrently with step2
            return StepData("some data")

        async def step2(collector: Collector, context: EventContext) -> StepData:
            payload = await collector['payload']
            # do something with payload, this can run concurrently with step1
            return StepData("some data")

        async def step3(collector: Collector, context: EventContext) -> StepData:
            step1data = await collector['step1']
            step2data = await collector['step2']
            # do something with step1data and step2data, step1 and step2 must be completed at this point
            return StepData("some combined data")

        async def seq_step4(collector: Collector, context: EventContext) -> SeqStepData:
            step3data = await collector['step3']
            # do something with step3data from the collector
            return SeqStepData("some data")

        async def seq_step5(payload: SeqStepData, context: EventContext) -> SeqStepData:
            # do something with payload (no need to use collector anymore)
            return SeqStepData("some data")

    Notice that collector steps can be combined with regular sequential steps. Each collector will create
    internally a single sequential step to be handled by the engine while the collector itself will
    handle execution for the steps specified in .gather(...) definition. After collector is executed
    the next sequential after the collector step will receive the `collector: Collector` as first argument.

    CAUTION: AsyncCollector makes not guarantees whether your code will block indefinitely (i,e.
    if you do `await collector['step1']` from step2func but step1func does `await collector['step2']`. This
    will block your application, so the only way the engine will prevent this to lock your server is
    using timeouts. In case of a dead-lock, event will fail to process and concurrent functions
    will be canceled when reaching a timeout, but no checking is done on whether a deadlock is happening.
    Please check the sequence your code is accessing/awaiting results from the collector to avoid cycles.
    """
    return CollectorStepsDescriptor(payload)
