"""hopeit.engine dataframes plugin SETUP event.

This event executes when engine starts with dataframes plugin configuration file loaded,
and ensures that the engine will support serialization of `@dataframe` and `@dataframeobject`
types
"""

from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger
from hopeit.dataframes.serialization.settings import DataframesSettings

from hopeit.dataframes.setup import registry

logger = app_logger()

__steps__ = ["setup"]


async def setup(payload: None, context: EventContext) -> None:
    """Setups serizaltion wrappers in hopeit.engine based on
    `DataSerialization` settings configured in plugin configuration file
    """
    logger.info(context, "Configuring Dataset serialization...")

    settings = context.settings(key="dataframes", datatype=DataframesSettings)

    logger.info(context, "Initializaing Dataframes Database registry...")
    await registry.init_registry(settings)

    logger.info(context, "Dataframes setup complete.")
