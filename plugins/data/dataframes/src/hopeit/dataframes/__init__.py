"""
hopeit.engine dataframes plugin entry point

This module exposes the 3 main constructions to be used inside apps:
`@dataframe` dataclass annotation
`@dataframeobject` dataclass annotation
`DataFrames` class to handle manipulation of dataframe/dataframeobjects

Usage:
```
from hopeit.dataframes import DataFrames, dataframe, dataframeobject

@dataframe
@dataclass
class MyDataFrame:
    field1: int
    field2: str
    ...

@dataframeobject
@dataclass
class MyDataset:
    dataset_name: str
    example_data: MyDataFrame


df = pd.DataFrame(...)  # create or load your pandas dataframe

my_data = DataFrames.from_df(pd.DataFrame(..))

return MyDataSet(
    dataset_name="example",
    example_data=my_data
)
```
"""

from typing import Dict, Generic, Iterator, List, Type

import numpy as np
import pandas as pd
from hopeit.dataframes.dataframe import DataFrameT, dataframe
from hopeit.dataframes.dataframeobject import DataFrameObjectT, dataframeobject
from hopeit.dataobjects import DataObject

__all__ = ["DataFrames", "dataframe", "dataframeobject"]


class DataFrames(Generic[DataFrameT, DataFrameObjectT, DataObject]):
    """
    Dataframes manipulation utilities methods
    """

    @staticmethod
    async def serialize(obj: DataFrameObjectT) -> DataObject:
        """Serialize/saves contents of dataframe fields of a `@dataframeobject`
        and converts to a `DataObject` json-compatible with pointers to saved
        locations.

        This method can be used to i.e. return `@dataframeobject`s as a JSON response
        """
        return await obj._serialize()  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    async def deserialize(
        datatype: Type[DataFrameObjectT], dataobject: DataObject
    ) -> DataFrameObjectT:
        """Deserialize/load contents of serialized dataobject fields of a `@dataframeobject`
        loading saved Dataset information for @dataframe fields
        """
        return await datatype._deserialize(dataobject)  # type: ignore  # pylint: disable=protected-access

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
        datatype: Type[DataFrameT], dataobjects: Iterator[DataFrameObjectT]
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
