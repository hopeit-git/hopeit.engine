from hopeit.dataframes.serialization.settings import (
    DataframesDatabaseSettings,
    DataframesSettings,
    DatasetSerialization,
)
from hopeit.fs_storage import FileStorage
from hopeit.redis_storage import RedisStorage

from hopeit.dataframes.serialization.protocol import find_protocol_impl

DEFAULT_DATABASE_KEY = "default"
db_cache: dict[str, object] = {}


registry: RedisStorage = RedisStorage()


class DataframesDatabaseRegistryError(Exception):
    pass


def _get_fs(settings: DataframesSettings) -> FileStorage:
    return FileStorage(path=settings.registry.save_location)


async def save_database_settings(
    settings: DataframesSettings, database_settings: DataframesDatabaseSettings
) -> None:
    await _get_fs(settings).store(database_settings.database_key, database_settings)


async def load_database_settings(
    settings: DataframesSettings, database_key: str
) -> DataframesDatabaseSettings | None:
    key = f"{settings.registry.save_location}/{database_key}"
    return await registry.get(key, datatype=DataframesDatabaseSettings)


async def init_registry(settings: DataframesSettings) -> None:
    impl = _get_storage_impl(settings.default_database.dataset_serialization)
    db_cache[DEFAULT_DATABASE_KEY] = impl

    registry.connect(
        address=settings.registry.connection_str,
        username=settings.registry.username.get_secret_value(),
        password=settings.registry.password.get_secret_value(),
    )
    for database_key in await list_databases(settings):
        await activate_database(settings, database_key)


async def activate_database(settings: DataframesSettings, database_key: str) -> None:
    db = await _get_fs(settings).get(database_key, datatype=DataframesDatabaseSettings)
    if db is None:
        raise DataframesDatabaseRegistryError(f"Database {database_key} not found in registry.")
    await registry.store(database_key, db)


async def list_databases(settings: DataframesSettings) -> list[str]:
    return [item.item_id for item in await _get_fs(settings).list_objects()]


async def db(database_key: str | None) -> DataframesDatabaseSettings | None:
    return await registry.get(
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


async def get_dataset_storage(database_key: str | None = None) -> object:
    impl = db_cache.get(database_key or DEFAULT_DATABASE_KEY)
    if impl is None:
        db_settings = await db(database_key)
        if db_settings is None:
            raise DataframesDatabaseRegistryError(f"{database_key} not found in database registry")
        impl = _get_storage_impl(db_settings.dataset_serialization)
        db_cache[database_key or DEFAULT_DATABASE_KEY] = impl
    return impl
