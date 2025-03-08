from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger

from hopeit.dataframes.setup import registry
from hopeit.dataframes.serialization.settings import DataframesDatabaseSettings

logger = app_logger()

__steps__ = ["register_database"]

__api__ = event_api(
    summary="Register Database",
    payload=DataframesDatabaseSettings,
    responses={200: DataframesDatabaseSettings},
)


async def register_database(
    payload: DataframesDatabaseSettings, context: EventContext
) -> DataframesDatabaseSettings:
    await registry.save_database_settings(payload)
    registered_db = await registry.db(payload.database_key)
    if registered_db is None:
        raise RuntimeError("Failed to register database.")
    return registered_db
