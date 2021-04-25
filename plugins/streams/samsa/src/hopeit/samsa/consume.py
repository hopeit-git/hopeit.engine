from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit.samsa import Batch, consume_in_process
import asyncio

logger, extra = app_extra_logger()

__steps__ = ['consume']


async def consume(payload: None, context: EventContext,
                  *, stream_name: str,
                  consumer_group: str, consumer_id: str,
                  batch_size: int=1, timeout_ms: int=1000) -> Batch:
    return await consume_in_process(
        stream_name=stream_name,
        consumer_group=consumer_group,
        consumer_id=consumer_id,
        batch_size=int(batch_size),
        timeout_ms=int(timeout_ms)
    )
