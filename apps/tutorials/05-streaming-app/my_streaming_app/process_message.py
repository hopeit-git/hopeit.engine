"""
Process Message:
===================================================================
Receive messages submitted to stream and saves data to disk as JSON
"""
import uuid
from typing import Optional, Union

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.toolkit.storage.fs import FileStorage

from .data_model import Status, MyMessage

logger, extra = app_extra_logger()

__steps__ = ['save_message']

output: FileStorage = None


async def __init_event__(context: EventContext):
    """
    Initializes output data saver using path configured in config.json
    """
    global output
    if output is None:
        save_path = context.env['process_message']['save_path']
        logger.info(context, "Initializing FileStorage...", extra=extra(path=save_path))
        output = FileStorage(path=save_path)


async def save_message(message: MyMessage, context: EventContext) -> MyMessage:
    """
    Receives `MyMessage` from stream, updates status and saves to disk.
    """
    assert output
    logger.info(context, "Received message", extra=extra(length=len(message.text)))
    message.status = Status.PROCESSED
    key = str(uuid.uuid4())
    saved_path = await output.store(key=key, value=message)
    logger.info(context, "Message saved", extra=extra(path=saved_path))
