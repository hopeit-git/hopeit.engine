from hopeit.dataobjects import dataclass

from typing import Union

from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import dataobject

__steps__ = ['produce_messages', SHUFFLE, 'process_a', 'process_b']

logger, extra = app_extra_logger()


@dataobject
@dataclass
class A:
    a: str


@dataobject
@dataclass
class B:
    b: str


async def produce_messages(payload: str, context: EventContext) -> Spawn[Union[A, B]]:
    logger.info(context, f"producing messages of type A and B from {payload}")
    a, b = payload.split('.')[:2]
    yield A(a)
    yield B(b)


async def process_a(payload: A, context: EventContext) -> str:
    logger.info(context, f"processing type A={payload}")
    return 'a: ' + payload.a


async def process_b(payload: B, context: EventContext) -> str:
    logger.info(context, f"processing type B={payload}")
    return 'b: ' + payload.b


async def __postprocess__(payload: B, context: EventContext, response: PostprocessHook) -> str:
    return "Events submitted."
