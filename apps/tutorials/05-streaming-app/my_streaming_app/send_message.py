"""
Send Message:
===============================================
Sends a message to be processed asynchronously
"""
from typing import Optional, Union

from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger

from .data_model import MyData, Status, MyMessage

logger, extra = app_extra_logger()

__steps__ = ['create_message', 'validate']

__api__ = event_api(
    payload=(MyData, "data received"),
    responses={
        200: (MyMessage, "message submitted to process"),
        400: (str, "invalid message error")
    }
)


async def create_message(payload: MyData, context: EventContext) -> MyMessage:
    """
    Creates MyMessage objects from the received text in MyData payload
    """
    logger.info(context, "Received data", extra=extra(length=len(payload.text)))
    message = MyMessage(payload.text, Status.NEW)
    return message


async def validate(message: MyMessage, context: EventContext) -> Optional[MyMessage]:
    """
    Validates the lenght of the text is at least 3 characters, then set status to VALID
    and return message to be submitted to stream. If message is not valid, None is returned and
    no message is sent to stream.
    """
    if len(message.text) < 3:
        return None
    message.status = Status.VALID
    return message


async def __postprocess__(message: Optional[MyMessage], context: EventContext,
                          response: PostprocessHook) -> Union[MyMessage, str]:
    """
    Special handler to customize what's returned as a response to the POST request received.
    Sets status to 400 if the message was invalid and returns just a message.
    Returns the validated message otherwise.
    Notice that this step can occur after MyMessage was already submitted to the stream.
    """
    if message is None:
        response.status = 400
        return "invalid data received"
    return message
