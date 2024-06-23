from datetime import datetime, timezone

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
from hopeit.dataframes import dataframe, dataframeobject
from pydantic.dataclasses import dataclass
# from hopeit.dataobjects import dataclass
from hopeit.testing.apps import create_test_context, execute_event, server_config


@dataframe
@dataclass
class MyTestData:
    number: int
    name: str
    timestamp: datetime


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


@dataframeobject
@dataclass
class MyTestDataObject:
    name: str
    data: MyTestData


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


async def setup_serialization_context(plugin_config) -> EventContext:
    context = create_test_context(
        app_config=plugin_config,
        event_name="setup.dataframes",
    )
    await execute_event(plugin_config, "setup.dataframes", payload=None)
    return context
