"""
Simple Example: Parallelize Event
--------------------------------------------------------------------
This example will spawn 2 copies of payload data, those are going to be send to a stream using SHUFFLE
and processed in asynchronously / in parallel if multiple nodes are available,
then submitted to other stream to be updated and saved
"""
from datetime import datetime, timezone
from typing import Optional, Union

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import dataobject
from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.logger import app_extra_logger
from hopeit.fs_storage import FileStorage, FileStorageSettings
from model import Something, SomethingStored, Status, StatusType

logger, extra = app_extra_logger()

__steps__ = ['fork_something', SHUFFLE, 'process_first_part', 'process_second_part', SHUFFLE, 'update_status', 'save']

__api__ = event_api(
    summary="Simple Example: Parallelize Event",
    payload=(Something, "Something object to forked and submitted to be processed concurrently"),
    responses={
        200: (str, 'events submitted successfully message')
    }
)


@dataobject
class FirstPart:
    data: Something


@dataobject
class SecondPart:
    data: Something


fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        settings: FileStorageSettings = context.settings(
            key="fs_storage", datatype=FileStorageSettings
        )
        fs = FileStorage.with_settings(settings)


async def fork_something(payload: Something, context: EventContext) -> Spawn[Union[FirstPart, SecondPart]]:
    """
    Produces 2 variants from payload to be processed in parallel
    """
    logger.info(context, "producing 2 variants of payload", extra=extra(something_id=payload.id))
    if payload.status:
        payload.history.append(payload.status)
    payload.status = Status(
        ts=datetime.now(tz=timezone.utc),
        type=StatusType.SUBMITTED
    )
    yield FirstPart(data=payload.copy(deep=True))
    yield SecondPart(data=payload.copy(deep=True))


async def __postprocess__(payload: Something, context: EventContext, response: PostprocessHook) -> str:  # noqa: C0103
    assert context.event_info.write_stream
    msg = f"events submitted to stream: {context.event_info.write_stream.name}"
    logger.info(context, msg)
    response.set_header("X-Stream-Name", context.event_info.write_stream.name)
    return msg


def process_first_part(payload: FirstPart, context: EventContext) -> Something:
    logger.info(context, "Processing FirstPart of id={payload.data.id}")
    payload.data.id = 'first_' + payload.data.id
    return payload.data


def process_second_part(payload: SecondPart, context: EventContext) -> Something:
    logger.info(context, f"Processing SecondPart of id={payload.data.id}")
    payload.data.id = 'second_' + payload.data.id
    return payload.data


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
        ts=datetime.now(timezone.utc),
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
