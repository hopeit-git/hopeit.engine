"""
Simple Example: Spawn Event
--------------------------------------------------------------------
This example will spawn 3 data events, those are going to be send to a stream using SHUFFLE
and processed in asynchronously / in parallel if multiple nodes are available
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import dataobject
from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.logger import app_extra_logger
from hopeit.fs_storage import FileStorage
from model import Something, Status, StatusType

logger, extra = app_extra_logger()

__steps__ = ['spawn_many_events', SHUFFLE, 'update_status', 'save']

__api__ = event_api(
    summary="Simple Example: Spawn Event",
    payload=(Something, "Something object to submitted several times to stream"),
    responses={
        200: (str, 'events submitted successfully message')
    }
)


@dataobject(event_id='payload.id', event_ts='payload.status.ts')
@dataclass
class SomethingStored:
    path: str
    payload: Something


fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


async def spawn_many_events(payload: Something, context: EventContext) -> Spawn[Something]:
    """
    Produces 3 events to be published to stream
    """
    logger.info(context, "spawning event 3 times", extra=extra(something_id=payload.id))
    if payload.status:
        payload.history.append(payload.status)
    for i in range(3):
        payload.status = Status(
            ts=datetime.now(tz=timezone.utc),
            type=StatusType.SUBMITTED
        )
        payload.id = str(i)
        yield payload


async def __postprocess__(payload: Something, context: EventContext, response: PostprocessHook) -> str:  # noqa: C0103
    assert context.event_info.write_stream
    msg = f"events submitted to stream: {context.event_info.write_stream.name}"
    logger.info(context, msg)
    response.set_header("X-Stream-Name", context.event_info.write_stream.name)
    return msg


def update_status(payload: Something, context: EventContext) -> Something:
    """
    Updates status of payload to PROCESSED and puts previous status in history.

    :param payload: Something, object
    :param context: EventContext
    """
    logger.info(context, "updating something status", extra=extra(something_id=payload.id))

    if payload.status:
        payload.history.append(payload.status)
    payload.status = Status(
        ts=datetime.now(),
        type=StatusType.PROCESSED
    )
    return payload


async def save(payload: Something, context: EventContext) -> SomethingStored:
    """
    Attempts to validate `payload` and save it to disk in json format

    :param payload: Something object
    :param context: EventContext
    """
    assert fs
    logger.info(context, "save", extra=extra(something_id=payload.id, path=fs.path))
    path = await fs.store(payload.id, payload)
    return SomethingStored(
        path=path,
        payload=payload
    )
