"""Support for plugin configuration"""

from typing import Optional

from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject, field

from hopeit.dataframes.serialization.protocol import find_protocol_impl

DEFAULT_DATABASE_KEY = "default"
db_cache: dict[str, object] = {}


class DataframesConfigurationError(Exception):
    pass


@dataobject
@dataclass
class DatasetSerialization:
    protocol: str
    location: str
    partition_dateformat: Optional[str] = None
    storage_settings: dict[str, str | int] = field(default_factory=dict)


@dataobject
@dataclass
class DataframesDatabaseSettings:
    dataset_serialization: DatasetSerialization


@dataobject
@dataclass
class DataframesSettings:
    databases: dict[str, DataframesDatabaseSettings]


def _get_effective_database_settings(
    key: str, settings: DataframesDatabaseSettings, context: EventContext
) -> tuple[str, DataframesDatabaseSettings]:
    def _replace_track_ids(original: str, context: EventContext) -> str:
        result = original
        for k, v in context.track_ids.items():
            result = result.replace("{{ context.track_ids." + k + " }}", v)
        return result

    ser_settings = settings.dataset_serialization
    return (
        _replace_track_ids(key, context),
        DataframesDatabaseSettings(
            dataset_serialization=DatasetSerialization(
                protocol=ser_settings.protocol,
                location=_replace_track_ids(ser_settings.location, context),
                partition_dateformat=(
                    None
                    if ser_settings.partition_dateformat is None
                    else _replace_track_ids(ser_settings.partition_dateformat, context)
                ),
                storage_settings=ser_settings.storage_settings,
            )
        ),
    )


def _get_databases(
    settings: DataframesSettings, context: EventContext
) -> dict[str, DataframesDatabaseSettings]:
    database_settings = {}
    for key, db in settings.databases.items():
        k, v = _get_effective_database_settings(key, db, context)
        database_settings[k] = v
    return database_settings


def _get_storage_impl(settings: DatasetSerialization) -> object:
    impl = find_protocol_impl(settings.protocol)
    return impl(
        protocol=settings.protocol,
        location=settings.location,
        partition_dateformat=settings.partition_dateformat,
        storage_settings=settings.storage_settings,
    )


def get_dataset_storage(context: EventContext, database_key: str | None = None) -> object:
    if database_key is None:
        database_key = DEFAULT_DATABASE_KEY
    impl = db_cache.get(database_key)
    if impl is None:
        raw_settings = context.settings(key="dataframes", datatype=DataframesSettings)
        dbs = _get_databases(raw_settings, context)
        try:
            serialization_settings = dbs[database_key].dataset_serialization
        except KeyError as e:
            raise DataframesConfigurationError(
                f"Database configuration not found in dataframes plugin settings: {database_key}"
            ) from e
        impl = _get_storage_impl(serialization_settings)
        db_cache[database_key] = impl
    return impl
