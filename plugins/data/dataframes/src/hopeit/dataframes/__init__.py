"""
hopeit.engine dataframes plugin entry point

This module exposes the 2 main constructions to be used inside apps,
to extend @dataobject functionallity supporting working with `pandas DataFrames`
`@dataframe` dataclass annotation
`DataFrames` class to handle manipulation of dataframe/dataframeobjects

Usage:
```
from typing import List

import pandas as pd

from hopeit.dataframes.serialization.settings import DatasetSerialization
from hopeit.dataframes import DataFrames, Dataset, dataframe
from hopeit.dataobjects import dataobject, dataclass
from hopeit.dataobjects.payload import Payload

@dataframe
@dataclass
class MyData:
    field1: int
    field2: str
    ...

@dataobject
@dataclass
class MyDataset:
    dataset_name: str
    example_data: Dataset[MyData]

@dataobject
@dataclass
class MyWebResponse:
    dataset_name: str
    example_data: List[MyData.DataObject]

# This step is not needed if SETUP event is configured in app
DataFrames.setup(DatasetSerialization(
      protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
      location="/tmp/data",
      partition_dateformat="%Y/%m/%d/%H/",
))

df = pd.DataFrame([  # Create or load a pandas DataFrame
    {"field1": 1, "field2": "text1"},
    {"field1": 2, "field2": "text2"},
])

my_data: MyData = DataFrames.from_df(MyData, df)

# return dataset after saving data to disk
my_dataset = MyDataset(
    dataset_name="example",
    example_data=await Dataset.save(my_data)
)

print(Payload.to_json(my_dataset))

my_data_again: MyData = await my_dataset.example_data.load()

print(DataFrames.df(my_data_again))

# return dataframe converted to list of dataobjects that can be directly converted to json
my_json_response = MyWebResponse(
    dataset_name="example",
    example_data=DataFrames.to_dataobjects(my_data)
)

print(Payload.to_json(my_json_response))
```
"""

from typing import Dict, Generic, Iterator, List, Type

import numpy as np
import pandas as pd
from hopeit.dataframes.dataframe import DataFrameT, dataframe
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataframes.serialization.settings import DatasetSerialization
from hopeit.dataframes.setup.dataframes import register_serialization
from hopeit.dataobjects import DataObject

__all__ = ["DataFrames", "Dataset", "dataframe"]


class DataFrames(Generic[DataFrameT, DataObject]):
    """
    Dataframes manipulation utilities methods
    """

    @staticmethod
    def setup(settings: DatasetSerialization):
        register_serialization(settings)

    @staticmethod
    def from_df(
        datatype: Type[DataFrameT], df: pd.DataFrame, **series: Dict[str, pd.Series]
    ) -> DataFrameT:
        """Create a `@dataframe` instance of a particular `datatype` from a pandas DataFrame.
        Optionally, add or override series.
        """
        return datatype._from_df(df, **series)  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def from_dataframe(
        datatype: Type[DataFrameT], obj: DataFrameT, **series: Dict[str, pd.Series]
    ) -> DataFrameT:
        """Creates a new `@dataframe` object extracting fields from another `@dataframe`"""
        return datatype._from_df(obj._df, **series)  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def from_dataobjects(
        datatype: Type[DataFrameT], dataobjects: Iterator[DataObject]
    ) -> DataFrameT:
        """Converts standard json serializable `@dataobject`s to a single `@dataframe`"""
        return datatype._from_dataobjects(dataobjects)  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def to_dataobjects(obj: DataFrameT) -> List[DataObject]:
        """Converts `@dataframe` object to a list of standard `@dataobject`s"""
        return obj._to_dataobjects()  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def from_array(datatype: Type[DataFrameT], array: np.ndarray) -> DataFrameT:
        """Creates `@dataframe` object from a numpy array"""
        return datatype._from_array(array)  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def df(obj: DataFrameT) -> pd.DataFrame:
        """Provides acces to the internal pandas dataframe of a `@dataframe` object"""
        return obj._df  # type: ignore  # pylint: disable=protected-access
