from unittest.mock import MagicMock
from hopeit.dataframes.serialization.dataset import Dataset, DatasetLoadError
from hopeit.dataobjects import copy_payload
import numpy as np
import pandas as pd
from pydantic import TypeAdapter, ValidationError
import pytest
import os

from conftest import (
    MyNumericalData,
    MyPartialTestData,
    MyTestData,
    MyTestDataAllOptional,
    MyTestDataOptionalValues,
    MyTestDataDefaultValues,
    MyTestDataObject,
    MyTestDataSchemaCompatible,
    MyTestDataSchemaNotCompatible,
    MyTestJsonDataObject,
    get_saved_file_path,
    setup_serialization_context,
)
from hopeit.app.config import AppConfig
from hopeit.dataframes import DataFrames
from pandas.testing import assert_frame_equal, assert_series_equal


def test_dataframes_from_df(sample_pandas_df: pd.DataFrame):
    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    assert len(DataFrames.df(initial_data)) == 100


def test_dataframes_from_df_not_nullable_number(sample_pandas_df: pd.DataFrame):
    sample_pandas_df.loc[0, "number"] = np.nan
    with pytest.raises(ValueError):
        DataFrames.from_df(MyTestData, sample_pandas_df)


def test_dataframes_from_df_not_nullable_string(sample_pandas_df: pd.DataFrame):
    sample_pandas_df.loc[0, "name"] = np.nan
    with pytest.raises(ValueError):
        DataFrames.from_df(MyTestData, sample_pandas_df)


def test_dataframes_from_df_all_null_values(sample_pandas_df: pd.DataFrame):
    sample_pandas_df["optional_value"] = np.nan
    sample_pandas_df["optional_label"] = np.nan
    initial_data = DataFrames.from_df(MyTestDataOptionalValues, sample_pandas_df)
    assert len(DataFrames.df(initial_data)) == 100
    assert initial_data.optional_value.isnull().all()  # type: ignore[union-attr]
    assert initial_data.optional_label.isnull().all()  # type: ignore[union-attr]


def test_dataframes_from_df_some_null_values(sample_pandas_df: pd.DataFrame):
    sample_pandas_df["optional_value"] = 100.0
    sample_pandas_df["optional_label"] = "optional"
    sample_pandas_df.loc[1, "optional_value"] = np.nan
    sample_pandas_df.loc[2, "optional_label"] = np.nan
    initial_data = DataFrames.from_df(MyTestDataOptionalValues, sample_pandas_df)
    assert len(DataFrames.df(initial_data)) == 100
    assert initial_data.optional_value.loc[0] == 100.0  # type: ignore[union-attr]
    assert np.isnan(initial_data.optional_value.loc[1])  # type: ignore[union-attr]
    assert initial_data.optional_value.loc[2] == 100.0  # type: ignore[union-attr]
    assert initial_data.optional_label.loc[1] == "optional"  # type: ignore[union-attr]
    assert np.isnan(initial_data.optional_label.loc[2])  # type: ignore[union-attr]
    assert initial_data.optional_label.loc[3] == "optional"  # type: ignore[union-attr]


def test_dataframes_from_df_set_optional_values(sample_pandas_df: pd.DataFrame):
    sample_pandas_df["optional_value"] = 100.0
    sample_pandas_df["optional_label"] = "optional"
    initial_data = DataFrames.from_df(MyTestDataOptionalValues, sample_pandas_df)
    assert len(DataFrames.df(initial_data)) == 100
    assert (initial_data.optional_value == 100.0).all()  # type: ignore[union-attr, attr-defined]
    assert (initial_data.optional_label == "optional").all()  # type: ignore[union-attr, attr-defined]


def test_dataframes_from_df_default_values(sample_pandas_df: pd.DataFrame):
    initial_data = DataFrames.from_df(MyTestDataDefaultValues, sample_pandas_df)
    assert len(DataFrames.df(initial_data)) == 100
    assert (initial_data.optional_value == 0.0).all()  # type: ignore[union-attr, attr-defined]
    assert (initial_data.optional_label == "(default)").all()  # type: ignore[union-attr, attr-defined]


def test_dataframes_from_dataframe(sample_pandas_df: pd.DataFrame):
    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    partial_data = DataFrames.from_dataframe(MyPartialTestData, initial_data)
    assert len(DataFrames.df(partial_data)) == 100
    assert_series_equal(partial_data.number, initial_data.number)  # type: ignore
    assert_series_equal(partial_data.name, initial_data.name)  # type: ignore


def test_dataframes_from_array():
    array = np.array([(n, 1.1 * n) for n in range(100)])
    numerical_data = DataFrames.from_array(MyNumericalData, array)
    assert_series_equal(numerical_data.number, pd.Series(array.T[0], name="number").astype(int))
    assert_series_equal(numerical_data.value, pd.Series(array.T[1], name="value"))


def test_dataobject_dataframes_conversion(one_element_pandas_df):
    data = DataFrames.from_df(MyTestData, one_element_pandas_df)
    objects = DataFrames.to_dataobjects(data)
    assert objects == [
        MyTestData.DataObject(number=1, name="test1", timestamp=objects[0].timestamp)
    ]
    back_to_dataframe = DataFrames.from_dataobjects(MyTestData, objects)
    assert_frame_equal(DataFrames.df(data), DataFrames.df(back_to_dataframe))


def test_dataobject_normalized_null_values(two_element_pandas_df_with_nulls):
    data = DataFrames.from_df(MyTestDataAllOptional, two_element_pandas_df_with_nulls)

    with pytest.raises(ValidationError):
        # nan values are not allowed
        DataFrames.to_dataobjects(data, normalize_null_values=False)

    objects = DataFrames.to_dataobjects(data, normalize_null_values=True)
    assert objects == [
        MyTestDataAllOptional.DataObject(
            id="1", number=1, name="test1", timestamp=objects[0].timestamp
        ),
        MyTestDataAllOptional.DataObject(id="2", number=None, name=None, timestamp=None),
    ]
    back_to_dataframe = DataFrames.from_dataobjects(MyTestDataAllOptional, objects)
    assert_frame_equal(DataFrames.df(data), DataFrames.df(back_to_dataframe))


async def test_dataframe_dataset_serialization_defaults(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data),
    )

    assert isinstance(dataobject.data, Dataset)
    assert dataobject.data.datatype == "conftest.MyTestData"
    assert isinstance(dataobject.data.partition_key, str)
    assert isinstance(dataobject.data.key, str)
    assert dataobject.data.protocol == "hopeit.dataframes.serialization.files.DatasetFileStorage"

    assert os.path.exists(get_saved_file_path(plugin_config, dataobject.data))

    loaded_obj = await Dataset.load(dataobject.data)

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(loaded_obj))


async def test_dataframe_dataset_serialization_schema_evolution(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data),
    )

    assert isinstance(dataobject.data, Dataset)
    assert dataobject.data.datatype == "conftest.MyTestData"
    assert isinstance(dataobject.data.partition_key, str)
    assert isinstance(dataobject.data.key, str)
    assert dataobject.data.protocol == "hopeit.dataframes.serialization.files.DatasetFileStorage"

    assert os.path.exists(get_saved_file_path(plugin_config, dataobject.data))

    loaded_obj = await Dataset.load(dataobject.data)

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(loaded_obj))


async def test_dataframe_dataset_serialization_save_schema(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data, save_schema=True),
    )

    assert isinstance(dataobject.data, Dataset)
    assert dataobject.data.datatype == "conftest.MyTestData"
    assert isinstance(dataobject.data.partition_key, str)
    assert isinstance(dataobject.data.key, str)
    assert dataobject.data.protocol == "hopeit.dataframes.serialization.files.DatasetFileStorage"

    assert dataobject.data.schema == TypeAdapter(MyTestData).json_schema()

    loaded_obj = await Dataset.load(dataobject.data)

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(loaded_obj))


async def test_dataframe_dataset_serialization_custom_database(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data, database_key="test_db"),
    )

    assert isinstance(dataobject.data, Dataset)
    assert dataobject.data.datatype == "conftest.MyTestData"
    assert isinstance(dataobject.data.partition_key, str)
    assert isinstance(dataobject.data.key, str)
    assert dataobject.data.protocol == "hopeit.dataframes.serialization.files.DatasetFileStorage"

    assert dataobject.data.database_key == "test_db"
    assert os.path.exists(get_saved_file_path(plugin_config, dataobject.data))

    loaded_obj = await Dataset.load(dataobject.data, database_key="test_db")

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(loaded_obj))


async def test_dataframe_dataset_serialization_custom_group(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data, database_key="test_db", group_key="custom/group"),
    )

    assert isinstance(dataobject.data, Dataset)
    assert dataobject.data.datatype == "conftest.MyTestData"
    assert isinstance(dataobject.data.partition_key, str)
    assert isinstance(dataobject.data.key, str)
    assert dataobject.data.protocol == "hopeit.dataframes.serialization.files.DatasetFileStorage"

    assert dataobject.data.database_key == "test_db"
    assert dataobject.data.group_key == "custom/group"
    assert os.path.exists(get_saved_file_path(plugin_config, dataobject.data))

    loaded_obj = await Dataset.load(dataobject.data, database_key="test_db")

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(loaded_obj))


async def test_dataframe_dataset_serialization_custom_collection(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(
            initial_data,
            database_key="test_db",
            group_key="custom/group",
            collection="my_collection",
        ),
    )

    assert isinstance(dataobject.data, Dataset)
    assert dataobject.data.datatype == "conftest.MyTestData"
    assert isinstance(dataobject.data.partition_key, str)
    assert isinstance(dataobject.data.key, str)
    assert dataobject.data.protocol == "hopeit.dataframes.serialization.files.DatasetFileStorage"

    assert dataobject.data.database_key == "test_db"
    assert dataobject.data.group_key == "custom/group"
    assert dataobject.data.collection == "my_collection"
    assert os.path.exists(get_saved_file_path(plugin_config, dataobject.data))

    loaded_obj = await Dataset.load(dataobject.data, database_key="test_db")

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(loaded_obj))


async def test_dataframe_dataset_serialization_storage_settings_used(
    monkeypatch, sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)

    df_mock = MagicMock()
    df_mock.return_value = b""
    monkeypatch.setattr(initial_data._df, "to_parquet", df_mock)  # type: ignore[attr-defined]

    _ = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data),
    )

    assert df_mock.call_count == 1
    assert df_mock.call_args[1]["compression"] == "zstd"
    assert df_mock.call_args[1]["compression_level"] == 22


async def test_dataframe_dataset_deserialization_compatible(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data),
    )

    modified_obj: Dataset[MyTestDataSchemaCompatible] = copy_payload(dataobject.data)  # type: ignore[assignment]
    modified_obj.datatype = "conftest.MyTestDataSchemaCompatible"
    loaded_obj = await Dataset.load(modified_obj)

    expected_df = DataFrames.df(initial_data)
    expected_df["new_optional_field"] = "(default)"

    assert_frame_equal(
        expected_df[["number", "timestamp", "new_optional_field"]], DataFrames.df(loaded_obj)
    )


async def test_dataframe_dataset_deserialization_not_compatible(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    await setup_serialization_context(plugin_config)

    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestDataObject(
        name="test",
        data=await Dataset.save(initial_data),
    )

    modified_obj: Dataset[MyTestDataSchemaNotCompatible] = copy_payload(dataobject.data)  # type: ignore[assignment]
    modified_obj.datatype = "conftest.MyTestDataSchemaNotCompatible"

    with pytest.raises(DatasetLoadError):
        await Dataset.load(modified_obj)


async def test_dataframe_json_object_serialization(
    sample_pandas_df: pd.DataFrame, plugin_config: AppConfig
):
    initial_data = DataFrames.from_df(MyTestData, sample_pandas_df)
    dataobject = MyTestJsonDataObject(
        name="test",
        data=DataFrames.to_dataobjects(initial_data),
    )

    assert all(isinstance(item, MyTestData.DataObject) for item in dataobject.data)  # type: ignore[attr-defined]

    original_data = DataFrames.from_dataobjects(MyTestData, dataobject.data)  # type: ignore[arg-type]

    assert_frame_equal(DataFrames.df(initial_data), DataFrames.df(original_data))
