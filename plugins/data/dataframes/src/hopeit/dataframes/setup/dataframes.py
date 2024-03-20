"""hopeit.engine dataframes plugin SETUP event.

This event executes when engine starts with dataframes plugin configuration file loaded,
and ensures that the engine will support serialization of `@dataframe` and `@dataframeobject`
types
"""

from functools import partial

from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger
from hopeit.dataframes.dataframeobject import DataFrameObjectMixin
from hopeit.dataframes.serialization.dataset import find_protocol_impl
from hopeit.dataframes.serialization.settings import DatasetSerialization
from hopeit.server import serialization

logger = app_logger()

__steps__ = ["register_serialization"]


def register_serialization(payload: None, context: EventContext) -> None:
    """Setups serizaltion wrappers in hopeit.engine based on
    `DataSerialization` settings configured in plugin configuration file
    """
    logger.info(context, "Registering serialization methods...")

    settings: DatasetSerialization = context.settings(
        key="dataset_serialization", datatype=DatasetSerialization
    )
    impl = find_protocol_impl(settings.protocol)

    storage = impl(
        protocol=settings.protocol,
        location=settings.location,
        partition_dateformat=settings.partition_dateformat,
    )
    setattr(DataFrameObjectMixin, "_DataFrameObjectMixin__storage", storage)

    serdeser_wrappers = {}
    for (
        serdeser,
        methods,
    ) in serialization._SERDESER.items():  # pylint: disable=protected-access
        serdeser_wrappers[serdeser] = (
            partial(storage.ser_wrapper, methods[0]),
            methods[1],
            partial(storage.deser_wrapper, methods[2]),
        )

    for serdeser, methods in serdeser_wrappers.items():
        serialization._SERDESER[serdeser] = methods  # pylint: disable=protected-access
