"""
Events base classes and low level handlers to execute events specified by apps
"""
from types import ModuleType
from typing import Dict, Optional, List, Tuple, AsyncGenerator
from asyncio import iscoroutine

from hopeit.dataobjects import EventPayload
from hopeit.server.steps import extract_postprocess_handler, execute_steps, StepInfo, \
    invoke_single_step, extract_module_steps, effective_steps, event_and_step
from hopeit.server.logger import setup_app_logger, engine_logger, extra_logger
from hopeit.server.imports import find_event_handler
from hopeit.app.config import AppConfig, EventDescriptor
from hopeit.app.context import EventContext, PostprocessHook

__all__ = ['EventHandler']

logger = engine_logger()
extra = extra_logger()


class EventHandler:
    """
    Handles execution of Hopeit App events
    """

    def __init__(self, *,
                 app_config: AppConfig,
                 plugins: List[AppConfig],
                 effective_events: Dict[str, EventDescriptor]):
        """
        Creates an EventHandler for a Hopeit App

        :param app_config: AppConfig, configuration for the App
        """
        self.app_config = app_config
        self.modules: Dict[str, Tuple[ModuleType, bool, list]] = {}
        self.steps: Dict[str, Dict[str, StepInfo]] = {}
        self.pp_handlers: Dict[str, Optional[StepInfo]] = {}
        logger.init_app(app_config, plugins)
        self.load_modules(effective_events)

    def load_modules(self, effective_events: Dict[str, EventDescriptor]):
        for event_name, event_info in effective_events.items():
            base_event, _ = event_and_step(event_name)
            module = find_event_handler(app_config=self.app_config, event_name=base_event)
            steps = extract_module_steps(module)
            self.modules[base_event] = (module, False, steps)
            self.pp_handlers[base_event] = extract_postprocess_handler(module)
            setup_app_logger(module, app_config=self.app_config, name=base_event, event_info=event_info)
            self.steps[event_name] = effective_steps(event_name, steps)

    async def handle_async_event(self, *,
                                 context: EventContext,
                                 query_args: Optional[dict],
                                 payload: Optional[EventPayload]) -> AsyncGenerator[Optional[EventPayload], None]:
        """
        Handles execution of engine defined event.
        Executes event handler code deployed with app.

        Execution goes as following:
            * EventDescriptor from AppConfig is used
            * an object from a class with CamelCase name same as event name is instantiated
            * find the next step to execute that accepts input with payload type
            * method with same name as step is invoked in instantiated object
            * if a step specifies write_stream, and event is not None, payload is published to a stream
            * repeats previous 3 steps executing next step that accepts current payload type

        :param context: EventContext
        :param query_args: arguments from a query context in the form of a dictionary
        :param payload: EventPayload, to be sent to event implementor
        """
        if query_args is None:
            query_args = {}
        base_event, _ = event_and_step(context.event_name)
        impl, initialized, raw_steps = self.modules[base_event]
        if not initialized:
            await self._init_module(module=impl, context=context)
            self.modules[base_event] = (impl, True, raw_steps)
        steps = self.steps[context.event_name]
        async for result in execute_steps(steps, context=context, payload=payload, **query_args):
            yield result

    async def postprocess(self, *,
                          context: EventContext,
                          payload: Optional[EventPayload],
                          response: PostprocessHook) -> Optional[EventPayload]:
        """
        Invokes postprocess method in event if defined in event configuration,
        allowing events to append headers, cookies and status to a response
        """
        pp_handler = self.pp_handlers[context.event_name]
        if pp_handler:
            _, initialized, _ = self.modules[context.event_name]
            assert initialized, \
                "Module not initialized. Postprocess requires events steps to be executed first"
            return await invoke_single_step(payload=payload, context=context, func=pp_handler[0], response=response)
        return payload

    async def _init_module(self, *, module, context: EventContext):
        if hasattr(module, '__init_event__'):
            logger.info(context, f"__init_event__ module={module.__name__}...")
            init_f = getattr(module, '__init_event__')
            coro_or_res = init_f(context)
            if iscoroutine(coro_or_res):
                await coro_or_res
