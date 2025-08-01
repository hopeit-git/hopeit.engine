from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

from hopeit.dataframes.serialization.settings import DataframesSettings
import numpy as np

# import pandas as pd
import polars as pl
import pytest
from hopeit.app.config import (
    AppConfig,
    AppDescriptor,
    AppEngineConfig,
    EventDescriptor,
    EventType,
)
from hopeit.app.context import EventContext
from hopeit.dataframes import Dataset, dataframe
from hopeit.dataobjects import dataclass, dataobject, field
from hopeit.testing.apps import create_test_context, execute_event, server_config


@dataframe
@dataclass
class MyTestData:
    number: int
    name: str
    timestamp: datetime


@dataframe
@dataclass
class MyTestDataAllOptional:
    id: str
    number: Optional[int]
    name: Optional[str]
    timestamp: Optional[datetime]


@dataframe
@dataclass
class MyTestDataOptionalValues:
    number: int
    name: str
    timestamp: datetime
    optional_value: Optional[float]
    optional_label: Optional[str]


@dataframe
@dataclass
class MyTestDataDefaultValues:
    number: int
    name: str
    timestamp: datetime
    optional_value: Optional[float] = 0.0
    optional_label: Optional[str] = "(default)"


@dataframe
@dataclass
class MyTestDataSchemaCompatible:
    number: int
    # Removed field: name
    timestamp: datetime
    # Added field with default value
    new_optional_field: str = field(default="(default)")


@dataframe
@dataclass
class MyTestDataSchemaNotCompatible:
    number: int
    name: str
    timestamp: datetime
    new_required_field: str


@dataframe
@dataclass
class MyNumericalData:
    number: int
    value: float


@dataframe
@dataclass
class MyPartialTestData:
    number: int
    name: str


@dataobject
@dataclass
class MyTestDataObject:
    name: str
    data: Dataset[MyTestData]


@dataobject
@dataclass
class MyTestJsonDataObject:
    name: str
    data: List[MyTestData.DataObject]  # type: ignore[name-defined]


@dataframe
@dataclass
class MyTestAllTypesData:
    int_value: int
    float_value: float
    str_value: str
    date_value: date
    datetime_value: datetime
    bool_value: bool
    int_value_optional: Optional[int]
    float_value_optional: Optional[float]
    str_value_optional: Optional[str]
    date_value_optional: Optional[date]
    datetime_value_optional: Optional[datetime]
    bool_value_optional: Optional[bool]


DEFAULT_DATE = datetime.now().date()
DEFAULT_DATETIME = datetime.now(tz=timezone.utc)


@dataframe
@dataclass
class MyTestAllTypesDefaultValues:
    id: str
    int_value: int = 1
    float_value: float = 1.0
    str_value: str = "(default)"
    date_value: date = DEFAULT_DATE
    datetime_value: datetime = DEFAULT_DATETIME
    bool_value: bool = False
    int_value_optional: Optional[int] = None
    float_value_optional: Optional[float] = None
    str_value_optional: Optional[str] = None
    date_value_optional: Optional[date] = None
    datetime_value_optional: Optional[datetime] = None
    bool_value_optional: Optional[bool] = None


@dataframe
@dataclass
class Part1:
    field0: str  # common field
    field1: str
    field2: float


@dataframe
@dataclass
class Part2:
    field0: str  # common field
    field3: str
    field4: float
    field5_opt: Optional[float] = None


@dataframe
@dataclass
class Part2Compat:
    field0: str  # common field
    field3: str
    field4: float
    field5_opt: Optional[float] = None
    field6_opt: Optional[int] = None
    field7_opt: Optional[str] = None


@dataframe
@dataclass
class Part1NoCompat:
    field0: str  # common field
    field1: str
    field2: float
    field8: float  # Added a required field


@dataobject
@dataclass
class MyDataBlock:
    block_id: str
    block_field: Optional[int]
    part1: Dataset[Part1]
    part2: Dataset[Part2]


@dataobject
@dataclass
class MyDataBlockCompat:
    block_id: str
    block_field: Optional[int]
    part1: Dataset[Part1]
    part2: Dataset[Part2Compat]


@dataobject
@dataclass
class MyDataBlockNoCompat:
    block_id: str
    block_field: Optional[int]
    part1: Dataset[Part1NoCompat]
    part2: Dataset[Part2Compat]


@dataobject
@dataclass
class MyDataBlockItem:
    block_id: str
    block_field: Optional[int]
    part1: Part1.DataObject  # type: ignore[name-defined]
    part2: Part2.DataObject  # type: ignore[name-defined]


@pytest.fixture
def one_element_pandas_df() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "number": 1,
                "name": "test1",
                "timestamp": datetime.now(tz=timezone.utc),
            }
        ]
    )


@pytest.fixture
def two_element_pandas_df_with_nulls() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "id": "1",
                "number": 1,
                "name": "test1",
                "timestamp": datetime.now(tz=timezone.utc),
            },
            {"id": "2", "number": None, "name": None, "timestamp": None},
        ]
    )


@pytest.fixture
def sample_df() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "number": n,
                "name": f"test{n}",
                "timestamp": datetime.now(tz=timezone.utc),
            }
            for n in range(100)
        ]
    )


@pytest.fixture
def plugin_config() -> AppConfig:
    return AppConfig(
        app=AppDescriptor(name="hopeit.dataframes.test", version="test"),
        engine=AppEngineConfig(
            import_modules=["hopeit.dataframes"],
        ),
        settings={
            "dataframes": {
                "registry": {"save_location": "/tmp/hopeit/dataframes/test/registry"},
                "default_database": {
                    "database_key": "default",
                    "dataset_serialization": {
                        "protocol": "hopeit.dataframes.serialization.files.DatasetFileStorage",
                        "location": "/tmp/hopeit/dataframes/test/data/default",
                        "partition_dateformat": "%Y/%m/%d/%H/",
                        "storage_settings": {"compression": "zstd", "compression_level": 22},
                    },
                },
            }
        },
        events={
            "setup.dataframes": EventDescriptor(type=EventType.SETUP, setting_keys=["dataframes"]),
            "setup.register_database": EventDescriptor(
                type=EventType.POST, setting_keys=["dataframes"]
            ),
        },
        server=server_config(),
    ).setup()


@pytest.fixture
def datablock_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "block_id": ["b1", "b1"],
            "block_field": [42, 42],
            "field0": ["item1", "item2"],
            "field1": ["f11", "f12"],
            "field2": [2.1, 2.2],
            "field3": ["f31", "f32"],
            "field4": [4.1, 4.2],
            "field5_opt": [5.1, None],
            "field6_opt": [None, None],
            "field7_opt": [None, None],
        }
    )


async def setup_serialization_context(plugin_config) -> EventContext:
    # Initializes default database
    context = create_test_context(
        app_config=plugin_config,
        event_name="setup.dataframes",
    )
    await execute_event(plugin_config, "setup.dataframes", payload=None)

    # Registers `test_db` custom database
    settings: DataframesSettings = context.settings(key="dataframes", datatype=DataframesSettings)
    payload = settings.default_database
    payload.database_key = "test_db"
    payload.dataset_serialization.location = payload.dataset_serialization.location.replace(
        "/default", "/test_db"
    )
    context = create_test_context(
        app_config=plugin_config,
        event_name="setup.register_database",
    )
    await execute_event(plugin_config, "setup.register_database", payload=payload)

    return context


def get_saved_file_path(plugin_config, dataset: Dataset) -> Path:
    context = create_test_context(
        app_config=plugin_config,
        event_name="setup.dataframes",
    )
    settings: DataframesSettings = context.settings(key="dataframes", datatype=DataframesSettings)
    payload = settings.default_database
    path = Path(
        payload.dataset_serialization.location.replace(
            "/default", f"/{dataset.database_key or 'default'}"
        )
    )
    if dataset.group_key:
        path = path / dataset.group_key
    if dataset.collection:
        path = path / dataset.collection
    if dataset.partition_key:
        path = path / dataset.partition_key
    return path / dataset.key
