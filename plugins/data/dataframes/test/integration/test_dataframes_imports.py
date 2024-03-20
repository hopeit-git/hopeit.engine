import pandas as pd
from conftest import MyTestData, MyTestDataObject
from hopeit.dataframes import *
from hopeit.dataframes.dataframe import DataFrameMixin
from hopeit.dataframes.dataframeobject import DataFrameObjectMixin


def test_dataframes_imports():
    assert DataFrames is not None
    assert dataframe is not None
    assert dataframeobject is not None


def test_dataframe_object_construction(one_element_pandas_df: pd.DataFrame):
    test_data = DataFrames.from_df(MyTestData, one_element_pandas_df)
    assert isinstance(test_data, DataFrameMixin)

    test_dataobject = MyTestDataObject(
        name="test",
        data=test_data,
    )
    assert isinstance(test_dataobject, DataFrameObjectMixin)
