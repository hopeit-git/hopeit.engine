import numpy as np
import pandas as pd

from conftest import (
    MyNumericalData,
    MyPartialTestData,
    MyTestData,
    MyTestDataObject,
    setup_serialization_context,
)
from hopeit.app.config import AppConfig
from hopeit.dataframes import DataFrames
from pandas.testing import assert_frame_equal, assert_series_equal


def test_dataframes_from_df(sample_pandas_df: pd.DataFrame):
    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    assert len(DataFrames.df(initial_data)) == 100


def test_dataframes_from_dataframe(sample_pandas_df: pd.DataFrame):
    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    partial_data = DataFrames.from_dataframe(MyPartialTestData, initial_data)
    assert len(DataFrames.df(partial_data)) == 100
    assert_series_equal(partial_data.number, initial_data.number)  # type: ignore
    assert_series_equal(partial_data.name, initial_data.name)  # type: ignore


def test_dataframes_from_array():
    array = np.array([(n, 1.1 * n) for n in range(100)])
    numerical_data = DataFrames.from_array(MyNumericalData, array)
    assert_series_equal(
        numerical_data.number, pd.Series(array.T[0], name="number").astype(int)
    )
    assert_series_equal(numerical_data.value, pd.Series(array.T[1], name="value"))


def test_dataobject_dataframes_conversion(one_element_pandas_df):
    data = DataFrames.from_df(MyTestData, one_element_pandas_df)
    objects = DataFrames.to_dataobjects(data)
    assert objects == [
        MyTestData.__dataframe__.serialized_type(
            number=1, name="test1", timestamp=objects[0].timestamp
        )
    ]
    back_to_dataframe = DataFrames.from_dataobjects(MyTestData, objects)
    assert_frame_equal(DataFrames.df(data), DataFrames.df(back_to_dataframe))


async def test_dataframe_object_serialization(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=initial_data,
    )
    saved_obj = await DataFrames.serialize(dataobject)  # type: ignore
    loaded_obj = await DataFrames.deserialize(MyTestDataObject, saved_obj)

    assert_frame_equal(DataFrames.df(dataobject.data), DataFrames.df(loaded_obj.data))
