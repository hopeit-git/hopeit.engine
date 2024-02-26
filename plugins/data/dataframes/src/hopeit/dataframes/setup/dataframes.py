from functools import partial

from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger
from hopeit.dataframes.dataframeobject import DataframeObjectMixin
from hopeit.dataframes.serialization.dataset import find_protocol_impl
from hopeit.dataframes.serialization.settings import DatasetSerialization
from hopeit.server import serialization

logger = app_logger()

__steps__ = ["register_serialization"]


def register_serialization(payload: None, context: EventContext) -> None:
    logger.info(context, "Registering serialization methods...")

    settings: DatasetSerialization = context.settings(
        key="dataset_serialization", datatype=DatasetSerialization
    )
    impl = find_protocol_impl(settings.protocol)

    storage = impl(protocol=settings.protocol, location=settings.location)
    setattr(DataframeObjectMixin, "_DataframeObjectMixin__storage", storage)

    serdeser_wrappers = {}
    for serdeser, methods in serialization._SERDESER.items():
        serdeser_wrappers[serdeser] = (
            partial(storage.ser_wrapper, methods[0]),
            methods[1],
            partial(storage.deser_wrapper, methods[2]),
        )

    for serdeser, methods in serdeser_wrappers.items():
        serialization._SERDESER[serdeser] = methods

    return None
