from dataclasses import dataclass
from datetime import datetime, timezone
from hopeit.dataframes import *
from hopeit.dataframes.dataframe import DataFrameMixin
from hopeit.dataframes.dataframeobject import DataFrameObjectMixin
import pandas as pd

@dataframe
@dataclass
class MyTestData:
    number: int
    name: str
    timestamp: datetime


@dataframeobject
@dataclass
class MyTestDataObject:
    name: str
    data: TestData


def test_dataframes_imports():
    assert DataFrames is not None
    assert dataframe is not None
    assert dataframeobject is not None

    test_data = DataFrames.from_df(MyTestData, pd.DataFrame(
        [{
            "number": 1, "name": "test1", "timestamp": datetime.now(tz=timezone.utc),
        }]
    ))
    assert isinstance(test_data, DataFrameMixin)

    test_dataobject = MyTestDataObject(
        name="test",
        data=test_data,
    )
    assert isinstance(test_dataobject, DataFrameObjectMixin)
