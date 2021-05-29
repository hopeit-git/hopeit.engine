"""
Handling sequencing and execution of steps from events
"""
import asyncio
from datetime import datetime
from functools import partial
from types import ModuleType
from typing import Type, Dict, Any, Optional, Callable, Tuple, AsyncGenerator, List, Union
import inspect
from copy import copy

from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, EventType, \
    ReadStreamDescriptor, StreamQueueStrategy, WriteStreamDescriptor
from hopeit.app.context import EventContext
from hopeit.dataobjects import EventPayload, copy_payload, EventPayloadType
from hopeit.server.imports import find_event_handler
from hopeit.server.logger import engine_logger, extra_logger
from hopeit.server.names import auto_path
from hopeit.server.collector import Collector, AsyncCollector, CollectorStepType

__all__ = ['extract_module_steps',
           'effective_steps',
           'event_and_step',
           'extract_event_stages',
           'extract_preprocess_handler',
           'extract_postprocess_handler',
           'extract_input_type',
           'execute_steps',
           'invoke_single_step',
           'find_datatype_handler',
           'StepInfo',
           'split_event_stages',
           'SHUFFLE',
           'CollectorStepsDescriptor']


SHUFFLE = '__shuffle__'

StepInfo = Tuple[Callable, Type, Type]

logger = engine_logger()
extra = extra_logger()


def extract_module_steps(impl: ModuleType) -> List[Tuple[str, Optional[StepInfo]]]:
    assert hasattr(impl, '__steps__'), f"Missing `__steps__` definition in module={impl.__name__}"
    return [
        (step_name, None if step_name == SHUFFLE else _signature(impl, step_name))
        for step_name in getattr(impl, '__steps__')
    ]


def effective_steps(event_name: str,
                    module_steps: List[Tuple[str, Optional[StepInfo]]]) -> Dict[str, StepInfo]:
    """
    Return list of steps given the possibility that event steps are splitted in stages
    using SHUFFLE keyword. Imn that case event name will contain `event_name.stage_step` format.
    In case event_name does not contain '.' and stage_step, the list of steps from start
    up to a SHUFFLE if found is returned. In case event_name hast '.' and stage_step,
    steps starting in stage_step up to the next SHUFFLE step if present is are returned.
    """
    steps: List[Tuple[str, StepInfo]] = []
    _, from_step = event_and_step(event_name)
    found = (from_step is None)
    for step_name, step_info in module_steps:
        if found:
            if step_name == SHUFFLE:
                break
            assert step_info
            steps.append((step_name, step_info))
        elif step_name == from_step:
            found = True
            assert step_info
            steps.append((step_name, step_info))
    return dict(steps)


def extract_event_stages(impl: ModuleType) -> List[str]:
    """
    Extract a list of step names consisting of the first step defined in __steps__ plus
    the subsequent step name after a SHUFFLE step if any in a given module
    """
    assert hasattr(impl, '__steps__'), f"Missing `__steps__` definition in module={impl.__name__}"
    stages = []
    steps = getattr(impl, '__steps__')
    if len(steps) == 1:
        return steps
    stage = steps[0] if isinstance(steps[0], str) else steps[0].__name__
    for step_name in steps[1:]:
        if step_name == SHUFFLE:
            assert stage, f"Invalid location of `SHUFFLE` step in module={impl.__name__}"
            stages.append(stage)
            stage = None
        elif stage is None:
            stage = step_name
    if stage:
        stages.append(stage)
    return stages


def extract_postprocess_handler(impl: ModuleType) -> Optional[StepInfo]:
    if hasattr(impl, '__postprocess__'):
        return _signature(impl, '__postprocess__')
    return None


def extract_preprocess_handler(impl: ModuleType) -> Optional[StepInfo]:
    if hasattr(impl, '__preprocess__'):
        return _signature(impl, '__preprocess__')
    return None


def extract_input_type(impl: ModuleType, from_step: Optional[str] = None) -> Type:
    assert hasattr(impl, '__steps__'), f"Missing `__steps__` definition in module={impl.__name__}"
    for step_name in getattr(impl, '__steps__'):
        if from_step is None or step_name == from_step:
            _, input_type, _ = _signature(impl, step_name)
            return input_type
    raise NotImplementedError(f"Cannot find payload datatype for module={impl.__name__} step={from_step}")


def event_and_step(event_name: str) -> Tuple[str, Optional[str]]:
    comps = event_name.split('$')
    if len(comps) > 1:
        return comps[0], comps[1]
    return event_name, None


async def execute_steps(steps: Dict[str, StepInfo], *,
                        context: EventContext,
                        payload: Optional[EventPayload],
                        **kwargs) -> AsyncGenerator[Optional[EventPayload], None]:
    """
    Invoke steps from a event.
    It will try to find next step in configuration order that matches input type of the payload,
    and will updated the payload and invoke next valid step.
    """
    start_ts = datetime.now()
    step_name, func = _find_next_step(payload, pending_steps=steps)
    if step_name:
        assert step_name
        assert func is not None, f"Cannot find implementation for step={context.event_name}.{step_name}"
        payload_copy = copy_payload(payload)
        async for invoke_result in _invoke_step(
                payload=payload_copy,
                func=func,
                context=context,
                disable_spawn=False,
                **kwargs):
            invoke_result = copy_payload(invoke_result)
            sub_steps = copy(steps)
            del sub_steps[step_name]
            yield await _execute_sub_steps(sub_steps, start_ts=start_ts, context=context, payload=invoke_result)
            start_ts = datetime.now()


async def _execute_sub_steps(steps: Dict[str, StepInfo], *,
                             start_ts: datetime,
                             context: EventContext,
                             payload: Optional[EventPayload]) -> Optional[EventPayload]:
    """
    Invoke steps from a event.
    It will try to find next step in configuration order that matches input type of the payload,
    and will updated the payload and invoke next valid step.
    """
    curr_obj = payload
    step_delay = context.event_info.config.stream.step_delay / 1000.0
    steps = copy(steps)
    step_name, func = _find_next_step(curr_obj, pending_steps=steps)
    while step_name:
        assert step_name
        assert func is not None, f"Cannot find implementation for step={context.event_name}.{step_name}"
        if step_delay:
            await asyncio.sleep(step_delay)
        async for invoke_result in _invoke_step(
                payload=curr_obj,
                func=func,
                context=context,
                disable_spawn=True):
            invoke_result = copy_payload(invoke_result)
            curr_obj = invoke_result
        del steps[step_name]
        step_name, func = _find_next_step(curr_obj, pending_steps=steps)
    await _throttle(context, start_ts)
    return curr_obj


async def invoke_single_step(func: Callable, *,
                             payload: Optional[EventPayload],
                             context: EventContext,
                             **kwargs) -> Optional[EventPayload]:
    payload_copy = copy_payload(payload)
    async for res in _invoke_step(payload=payload_copy, func=func, context=context, disable_spawn=True, **kwargs):
        return res
    return None


async def _invoke_step(*,
                       payload: Optional[EventPayload],
                       func: Callable,
                       context: EventContext,
                       disable_spawn: bool,
                       **kwargs) -> AsyncGenerator[Optional[EventPayload], None]:
    """
    Invokes step handler method
    """
    func_res = func(payload, context, **kwargs)
    if inspect.iscoroutine(func_res):
        yield await func_res
    elif isinstance(func_res, AsyncGenerator):  # pylint: disable=isinstance-second-argument-not-valid-type
        if disable_spawn:
            raise NotImplementedError(
                "`Spawn[...]` only supported in initial step."
                " Cannot execute `{func.__name__}`."
                " Insert `SHUFFLE` step after spawn event.")
        async for res in func_res:
            yield res
    else:
        yield func_res


def _find_next_step(payload: Optional[EventPayload], *,
                    pending_steps: Dict[str, StepInfo]) -> Tuple[Optional[str], Optional[Callable]]:
    """
    Finds next step to exectute in pending_steps list, base on the payload data type
    """
    for step_name, step_info in pending_steps.items():
        func, input_type, _ = step_info
        if input_type is None and payload is None:
            return step_name, func
        if input_type is not None and isinstance(payload, input_type):
            return step_name, func
    return None, None


async def _throttle(context: EventContext, start_ts: datetime):
    """
    Performs an async sleep in order to achieve duration specified by throttle configuration
    """
    throttle_ms = context.event_info.config.stream.throttle_ms
    delay = 0.0
    if throttle_ms:
        elapsed_td = datetime.now() - start_ts
        elapsed = 1000.0 * elapsed_td.total_seconds()
        delay = max(0.0, 1.0 * throttle_ms - elapsed)
    if delay > 0.0:
        logger.debug(context, "Throttling...",
                     extra=extra(prefix='throttle.', delay=delay, target=throttle_ms))
        await asyncio.sleep(delay / 1000.0)


def split_event_stages(app: AppDescriptor,
                       event_name: str,
                       event_info: EventDescriptor,
                       impl: ModuleType) -> Dict[str, EventDescriptor]:
    """
    Splits an event whose steps contain SHUFFLE step, in an initial event with same name as event_name
    plus sub_events with names `event_name.step_name' for each step after a SHUFFLE.
    Creates intermediate auto named write_stream, read_stream to communicate data between event and sub_events,
    clones event configuration from main event to sub_events, and setup write_stream property for final event
    to be the one specified in configuration.
    """
    event_stages = extract_event_stages(impl)
    if len(event_stages) == 1:
        return {event_name: event_info}

    effective_events: Dict[str, EventDescriptor] = {}
    event_type = event_info.type
    read_stream = event_info.read_stream
    queues = ["AUTO"] if read_stream is None else read_stream.queues
    sub_event_name: Optional[str] = event_name
    sub_event_info = event_info
    intermediate_stream = None
    for stage in event_stages:
        if sub_event_name is None:
            sub_event_name = f"{event_name}${stage}"
        if read_stream is None and intermediate_stream is not None:
            read_stream = ReadStreamDescriptor(
                name=intermediate_stream,
                consumer_group=auto_path(app.name, app.version, *event_name.split('.'), stage),
                queues=queues
            )
        intermediate_stream = auto_path(app.name, app.version, *event_name.split('.'), stage)
        sub_event_info = EventDescriptor(
            type=event_type,
            read_stream=read_stream,
            write_stream=WriteStreamDescriptor(
                name=intermediate_stream,
                queue_strategy=StreamQueueStrategy.PROPAGATE
            ),
            config=event_info.config
        )
        effective_events[sub_event_name] = sub_event_info
        event_type = EventType.STREAM
        sub_event_name = None
        read_stream = None
    # Set last stage write_stream to original event write_stream
    sub_event_info.write_stream = event_info.write_stream
    return effective_events


def find_datatype_handler(*, app_config: AppConfig, event_name: str):
    base_event, from_step = event_and_step(event_name)
    impl = find_event_handler(app_config=app_config, event_name=base_event)
    datatype = extract_input_type(impl, from_step=from_step)
    return datatype


class CollectorStepsDescriptor:
    """
    Specification for input payload type and list of sub-steps when using a collector as a compound steps
    in __steps__ definition of a method. This class should be instantiated using `collector` method
    from hopeit.app.events module.

    Example::

        from hopeit.app.events import collector_step

        __steps__ == [collector_step(payload=InputType).steps('step1', 'step2'), 'step_outside_collector']

    will generate a steps definition of two steps: First a collector, which receives an InputType object
    and run step1 and step2 functions concurrently. Step result will be a Collector to be used by
    `step_outside_collector`.
    """
    def __init__(self, input_type: Type[EventPayloadType]):
        self.input_type = input_type
        self.step_names: List[str] = []
        self.steps: Optional[List[Tuple[str, CollectorStepType]]] = None
        self.__name__ = f'collector@{id(self)}'

    def gather(self, *steps: str):
        self.step_names.extend(steps)
        self.__name__ = f'collector@{self.step_names[0]}'
        return self

    def __repr__(self) -> str:
        return f"collector(payload: {self.input_type.__name__}),\n  [" + \
               ',\n   '.join(f"'{name}'" for name in self.step_names) + ']'

    def name(self) -> str:
        return self.__name__

    def setup_step_impl(self, module: ModuleType) -> Callable[[EventPayload, EventContext], EventPayload]:
        if self.steps is None:
            self.steps = []
            for step_name in self.step_names:
                step_impl, payload_type, _ = _signature(module, step_name)
                assert step_impl is not None, "Collector can only contain function definitions."
                assert payload_type is AsyncCollector, f"step={step_name} first arg must be `Collector`"
                self.steps.append((step_name, step_impl))
        return partial(_run_collector, self)


async def _run_collector(step_group: CollectorStepsDescriptor, payload: EventPayload, context: EventContext):
    return await AsyncCollector().input(payload).steps(*step_group.steps).run(context)


def _signature(impl: ModuleType, step_name: Union[str, CollectorStepsDescriptor]) -> Tuple[Callable, Type, Type]:
    """
    Computes signature (`CollectorStepsDescriptor`) from a given step (def) in an event module. Results
    are used internally by the engine to compute input/output datatypes of events and find proper steps
    to handle payloads and results.
    """
    if isinstance(step_name, CollectorStepsDescriptor):
        func = step_name.setup_step_impl(impl)
        annotation = step_name.input_type
        return_annotation = Collector
    else:
        func = getattr(impl, step_name)
        signature = inspect.signature(func)
        payload_arg = next(iter(signature.parameters.values()))
        annotation = payload_arg.annotation if payload_arg.annotation is not inspect.Signature.empty else Any
        return_annotation = signature.return_annotation if signature.return_annotation else Any
    return func, annotation, return_annotation
