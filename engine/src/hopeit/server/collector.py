"""
AsyncCollector (aliased as Collector) implementation to be used as a way to concurrently execute steps in an event

Use `hopeit.app.events` `collector_step(...)` constructor to define steps implementing AsyncCollector
"""
import asyncio
from typing import Callable, Dict, Any, Tuple, Optional, Coroutine
from hopeit.dataobjects import copy_payload

from hopeit.app.context import EventContext

__all__ = ['Collector', 'AsyncCollector', 'CollectorStepType']


class AbstractCollector:
    async def run(self, context: EventContext) -> Any:
        raise NotImplementedError("AbstractCollector cannot be executed.")


CollectorStepType = Callable[[AbstractCollector, EventContext], Coroutine]


class CollectorItem:
    def __init__(self, func: CollectorStepType):
        self.func = func
        self.lock = asyncio.Lock()
        self.data: Any = None


class AsyncCollector(AbstractCollector):
    """
    Allows to define a list of steps (functions) to be executed concurrently.

    Example::

        AsyncCollector.input(payload).steps(('step1', step1func, 'step2', step2func').run()


    Gathers and run concurrently step1func and step2func and put their return values in the collector
    under the specified key ('step1' or 'step2')
    If a function needs the result from another step it can be retrieved with `await collector['step1'].
    To access the payload a function can do `payload = await collector['payload']
    This way you can specify a number of functions that can run asynchronously with no particular order
    (i.e. when querying multiple databases or making requests in parallel to external services),
    and then use the results or combine them in a different step.

    CAUTION: AsyncCollector makes not guarantees whether your code will block indefinitely (i,e.
    if you do `await collector['step1']` from step2func but step1func does `await collector['step2']`. This
    will block your application, so the only way the engine will prevent this to lock your server is
    using timeouts. In case of a dead-lock, event will fail to process and concurrent functions
    will be canceled when reaching a timeout, but no checking is done on whether a deadlock is happening.
    Please check the sequence your code is accessing/awaiting results from the collector to avoid cycles.
    """
    __data_object__ = {'unsafe': True, 'validate': False, 'schema': False}

    def __init__(self):
        self.items: Dict[str, CollectorItem] = {}
        self.executed: bool = False
        self.payload: Optional[Any] = None

    def input(self, payload: Any):
        self.payload = payload
        return self

    def steps(self, *funcs: Tuple[str, CollectorStepType]):
        for name, func in funcs:
            self.items[name] = CollectorItem(func)
        return self

    async def _get(self, name, lock=False) -> Any:
        """
        Locks and waits for a collector steps is computed and return its results.
        In case name is 'payload', returns collector input without blocking.
        """
        if name == 'payload':
            return copy_payload(self.payload)
        assert self.executed, "Collector not executed. Call collector.run(...) before accessing results."
        item = self.items[name]
        await item.lock.acquire()
        try:
            return copy_payload(item.data)
        finally:
            if not lock:
                item.lock.release()

    def __getitem__(self, item):
        return self._get(item)

    async def _run_item(self, item: CollectorItem, context: EventContext):
        assert item.lock.locked(), f"Step {item} already released."
        try:
            item.data = await item.func(self, context)
        finally:
            item.lock.release()

    async def run(self, context: EventContext):
        steps = []
        for item in self.items.values():
            await item.lock.acquire()
            steps.append(self._run_item(item, context))
        self.executed = True
        await asyncio.gather(*steps)
        return self


Collector = AsyncCollector
