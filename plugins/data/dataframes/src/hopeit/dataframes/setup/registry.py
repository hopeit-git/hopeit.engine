from typing import Optional
from hopeit.dataframes.serialization.settings import (
    DataframesDatabaseSettings,
    DataframesSettings,
    DatasetSerialization,
)
from hopeit.fs_storage import FileStorage

from hopeit.dataframes.serialization.protocol import find_protocol_impl

DEFAULT_DATABASE_KEY = "default"
db_cache: dict[str, object] = {}
persitent_registry: Optional[FileStorage] = None


class DataframesDatabaseRegistryError(Exception):
    pass


async def save_database_settings(database_settings: DataframesDatabaseSettings) -> None:
    assert persitent_registry, "Registry not initialized. Call `init_registry`"
    await persitent_registry.store(database_settings.database_key, database_settings)


async def load_database_settings(
    settings: DataframesSettings, database_key: str
) -> Optional[DataframesDatabaseSettings]:
    assert persitent_registry, "Registry not initialized. Call `init_registry`"
    key = f"{settings.registry.save_location}/{database_key}"
    return await persitent_registry.get(key, datatype=DataframesDatabaseSettings)


async def init_registry(settings: DataframesSettings) -> None:
    global persitent_registry
    persitent_registry = FileStorage(path=settings.registry.save_location)
    impl = _get_storage_impl(settings.default_database.dataset_serialization)
    db_cache[DEFAULT_DATABASE_KEY] = impl


async def list_databases(settings: DataframesSettings) -> list[str]:
    assert persitent_registry, "Registry not initialized. Call `init_registry`"
    return [item.item_id for item in await persitent_registry.list_objects()]


async def db(database_key: Optional[str]) -> Optional[DataframesDatabaseSettings]:
    assert persitent_registry, "Registry not initialized. Call `init_registry`"
    return await persitent_registry.get(
        database_key or DEFAULT_DATABASE_KEY, datatype=DataframesDatabaseSettings
    )


def _get_storage_impl(settings: DatasetSerialization) -> object:
    impl = find_protocol_impl(settings.protocol)
    return impl(
        protocol=settings.protocol,
        location=settings.location,
        partition_dateformat=settings.partition_dateformat,
        storage_settings=settings.storage_settings,
    )


async def get_dataset_storage(database_key: Optional[str] = None) -> object:
    impl = db_cache.get(database_key or DEFAULT_DATABASE_KEY)
    if impl is None:
        db_settings = await db(database_key)
        if db_settings is None:
            raise DataframesDatabaseRegistryError(f"{database_key} not found in database registry")
        impl = _get_storage_impl(db_settings.dataset_serialization)
        db_cache[database_key or DEFAULT_DATABASE_KEY] = impl
    return impl
