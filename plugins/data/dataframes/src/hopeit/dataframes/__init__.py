"""
hopeit.engine dataframes plugin entry point

This module exposes the 2 main constructions to be used inside apps,
to extend @dataobject functionallity supporting working with `polars DataFrames`
`@dataframe` dataclass annotation
`DataFrames` class to handle manipulation of dataframe/dataframeobjects

Usage:
```
from typing import List

import polars as pl

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

# Initialization: this step is not needed if SETUP event is configured in app
settings = DataframesSettings(...)  # settings example in `plugin-config.json`
await registry.init_registry(settings)

# Usage
df = pd.DataFrame([  # Create or load a polars DataFrame
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

try:
    import polars as pl
except ImportError:
    pl = None  # type: ignore[assignment] # Polars is optional; set to None if not installed

from hopeit.dataframes.dataframe import DataFrameT, dataframe
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataframes.datablocks import DataBlocks
from hopeit.dataobjects import DataObject

__all__ = ["DataBlocks", "DataFrames", "Dataset", "dataframe"]


class DataFrames(Generic[DataFrameT, DataObject]):
    """
    Dataframes manipulation utilities methods
    """

    @staticmethod
    def from_df(
        datatype: Type[DataFrameT], df: "pl.DataFrame", **series: Dict[str, "pl.Series"]
    ) -> DataFrameT:
        """Create a `@dataframe` instance of a particular `datatype` from a polars DataFrame.
        Optionally, add or override series.
        """
        return datatype._from_df(df, **series)  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def from_dataframe(
        datatype: Type[DataFrameT], obj: DataFrameT, **series: Dict[str, "pl.Series"]
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
    def df(obj: DataFrameT) -> "pl.DataFrame":
        """Provides acces to the internal `polars` dataframe of a `@dataframe` object"""
        return obj._df  # type: ignore  # pylint: disable=protected-access

    @staticmethod
    def schema(datatype: Type[DataFrameT]) -> "pl.Schema":
        if pl is None:
            raise RuntimeError(
                "`polars` needs to be installed to access dataframe schema. "
                "Run `pip install hopeit.dataframes[polars]`"
            )
        return datatype.__dataframe__.schema  # type: ignore  # pylint: disable=protected-access
