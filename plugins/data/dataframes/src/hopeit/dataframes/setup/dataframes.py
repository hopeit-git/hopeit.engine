"""hopeit.engine dataframes plugin SETUP event.

This event executes when engine starts with dataframes plugin configuration file loaded,
and ensures that the engine will support serialization of `@dataframe` and `@dataframeobject`
types
"""

from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger
from hopeit.dataframes.serialization.dataset import Dataset, find_protocol_impl
from hopeit.dataframes.serialization.settings import DatasetSerialization

logger = app_logger()

__steps__ = ["setup"]


def setup(payload: None, context: EventContext) -> None:
    """Setups serizaltion wrappers in hopeit.engine based on
    `DataSerialization` settings configured in plugin configuration file
    """
    logger.info(context, "Configuring Dataset serialization...")
    settings: DatasetSerialization = context.settings(
        key="dataset_serialization", datatype=DatasetSerialization
    )
    register_serialization(settings)


def register_serialization(settings: DatasetSerialization):
    impl = find_protocol_impl(settings.protocol)
    storage = impl(
        protocol=settings.protocol,
        location=settings.location,
        partition_dateformat=settings.partition_dateformat,
    )
    setattr(Dataset, "_Dataset__storage", storage)
