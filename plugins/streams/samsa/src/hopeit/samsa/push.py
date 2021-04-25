from hopeit.app.context import EventContext

from hopeit.samsa import Batch, push_in_process


__steps__ = ['push']


async def push(payload: Batch, context: EventContext, 
               stream_name: str, producer_id: str, maxlen: int) -> int:
    return await push_in_process(
        batch=payload,
        stream_name=stream_name,
        producer_id=producer_id,
        maxlen=int(maxlen)
    )
