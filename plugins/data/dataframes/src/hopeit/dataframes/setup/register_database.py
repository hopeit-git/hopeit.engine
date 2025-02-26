import asyncio
from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_logger

from hopeit.dataframes.setup import registry
from hopeit.dataframes.serialization.settings import DataframesDatabaseSettings, DataframesSettings

logger = app_logger()

__steps__ = ["register_database"]

__api__ = event_api(summary="Register Database", payload=DataframesDatabaseSettings, responses={200: DataframesDatabaseSettings})


async def register_database(payload: DataframesDatabaseSettings, context: EventContext) -> DataframesDatabaseSettings:
    settings = context.settings(key="dataframes", datatype=DataframesSettings)
    await registry.save_database_settings(settings, payload)
    await asyncio.sleep(0.0)
    await registry.activate_database(settings, payload.database_key)
    return payload


# def register_serialization(settings: DatasetSerialization) -> None:
#     impl = find_protocol_impl(settings.protocol)
#     storage = impl(
#         protocol=settings.protocol,
#         location=settings.location,
#         partition_dateformat=settings.partition_dateformat,
#         storage_settings=settings.storage_settings,
#     )
#     # setattr(Dataset, "_Dataset__storage", storage)
