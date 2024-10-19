from datetime import date, datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd
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
    field1: str
    field2: float


@dataframe
@dataclass
class Part2:
    field3: str
    field4: float
    field5_opt: Optional[float] = None


@dataobject
@dataclass
class MyDataBlock:
    block_id: str
    block_field: Optional[int]
    part1: Dataset[Part1]
    part2: Dataset[Part2]


@dataobject
@dataclass
class MyDataBlockItem:
    block_id: str
    block_field: Optional[int]
    part1: Part1.DataObject
    part2: Part2.DataObject


@pytest.fixture
def one_element_pandas_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "number": 1,
                "name": "test1",
                "timestamp": datetime.now(tz=timezone.utc),
            }
        ]
    )


@pytest.fixture
def two_element_pandas_df_with_nulls() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id": "1",
                "number": 1,
                "name": "test1",
                "timestamp": datetime.now(tz=timezone.utc),
            },
            {"id": "2", "number": np.nan, "name": None, "timestamp": pd.NaT},
        ]
    )


@pytest.fixture
def sample_pandas_df() -> pd.DataFrame:
    return pd.DataFrame(
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
def plugin_config() -> EventContext:
    return AppConfig(
        app=AppDescriptor(name="hopeit.dataframes.test", version="test"),
        engine=AppEngineConfig(
            import_modules=["hopeit.dataframes"],
        ),
        settings={
            "dataset_serialization": {
                "protocol": "hopeit.dataframes.serialization.files.DatasetFileStorage",
                "location": "/tmp/hopeit/dataframes/test",
                "partition_dateformat": "%Y/%m/%d/%H/",
            }
        },
        events={
            "setup.dataframes": EventDescriptor(
                type=EventType.SETUP, setting_keys=["dataset_serialization"]
            )
        },
        server=server_config(),
    ).setup()


@pytest.fixture
def datablock_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "block_id": ["b1", "b1"],
            "block_field": [42, 42],
            "field1": ["f11", "f12"],
            "field2": [2.1, 2.2],
            "field3": ["f31", "f32"],
            "field4": [4.1, 4.2],
            "field5_opt": [5.1, None],
        }
    )


async def setup_serialization_context(plugin_config) -> EventContext:
    context = create_test_context(
        app_config=plugin_config,
        event_name="setup.dataframes",
    )
    await execute_event(plugin_config, "setup.dataframes", payload=None)
    return context
