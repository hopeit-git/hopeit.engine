from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from hopeit.dataobjects import DataObject
from hopeit.dataobjects.payload import Payload

__steps__ = ['entry_point']

logger, extra = app_extra_logger()


def entry_point(payload: DataObject, context: EventContext) -> str:
    logger.info(context, "mock_event_dataobject_payload.entry_point")
    return Payload.to_json(payload)
