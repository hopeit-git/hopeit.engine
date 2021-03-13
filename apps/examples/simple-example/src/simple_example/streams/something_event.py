"""
Simple Example: Something Event
--------------------------------------------------------------------
Submits a Something object to a stream to be processed asynchronously by process-events app event
"""
from datetime import datetime, timezone

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from model import Something, Status, StatusType

__steps__ = ['stream_event']

logger, extra = app_extra_logger()

__api__ = event_api(
    summary="Simple Example: Something Event",
    payload=(Something, "Something object to submitted to stream"),
    responses={
        200: (Something, 'Updated Something object with status submitted to string')
    }
)


def stream_event(payload: Something, context: EventContext) -> Something:
    logger.info(context, "streaming event", extra=extra(something_id=payload.id))
    if payload.status:
        payload.history.append(payload.status)
    payload.status = Status(
        ts=datetime.now(tz=timezone.utc),
        type=StatusType.SUBMITTED
    )
    return payload
