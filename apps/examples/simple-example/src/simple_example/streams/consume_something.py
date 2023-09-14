"""
Simple Example: Consume Something
--------------------------------------------------------------------
Loads Something from disk
"""
from typing import Union, Optional
from datetime import datetime, timezone

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_extra_logger
from hopeit.server.engine import AppEngine
from model import Something, StatusType, Status, SomethingNotFound

from hopeit.server import runtime

__steps__ = ["consume"]

__api__ = event_api(
    summary="Simple Example: Consume Something",
    query_args=[
        ("consumer_group", Optional[str], "Consumer group name"),
    ],
    responses={
        200: (Something, "Something object returned when consumed"),
        404: (SomethingNotFound, "Nothing to consume"),
    },
)

logger, extra = app_extra_logger()


async def consume(
    payload: None, context: EventContext, *, consumer_group: Optional[str] = None
) -> Something | SomethingNotFound:
    
    app_engine: AppEngine = runtime.server.app_engines[context.app_key]
    
    if consumer_group is None:
        consumer_group = context.event_info.read_stream.consumer_group

    await app_engine.stream_manager.ensure_consumer_group(
        stream_name=context.event_info.read_stream.name,
        consumer_group=consumer_group,
    )

    events = await app_engine.stream_manager.read_stream(
        stream_name=context.event_info.read_stream.name,
        consumer_group=consumer_group,
        datatypes={"model.Something": Something},
        track_headers=context.track_ids,
        offset=">",
        batch_size=1,
        timeout=10,
        batch_interval=1000,
    )

    if len(events) == 0:
        return SomethingNotFound(
            path=context.event_info.read_stream.name,
            id=context.event_info.read_stream.consumer_group,
        )

    return events[0].payload


async def __postprocess__(
    payload: Something | SomethingNotFound,
    context: EventContext,
    response: PostprocessHook,
) -> Something | SomethingNotFound:
    if isinstance(payload, SomethingNotFound):
        response.status = 404
    return payload
