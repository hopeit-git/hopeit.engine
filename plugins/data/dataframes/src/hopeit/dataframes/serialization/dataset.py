"""Dataset objects definition, used as a result of serialized dataframes"""

from importlib import import_module
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from hopeit.dataobjects import dataclass, dataobject, field
import pandas as pd
from pydantic import TypeAdapter

DataFrameT = TypeVar("DataFrameT")
GenericDataFrameT = TypeVar("GenericDataFrameT")


class DatasetLoadError(Exception):
    pass


class DatasetConvertError(Exception):
    pass


@dataobject
@dataclass
class Dataset(Generic[DataFrameT]):
    """Persisted representation of a @dataframe object"""

    protocol: str
    partition_key: str
    key: str
    datatype: str
    schema: Dict[str, Any] = field(default_factory=dict)

    async def load(self) -> DataFrameT:
        try:
            df = await self.load_df()
            return self.convert(self, df)
        except DatasetConvertError as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading dataset of type {self.datatype} "
                f"at location {self.partition_key}/{self.key}"
            ) from e

    async def load_df(self, *, columns: Optional[list[str]] = None) -> pd.DataFrame:
        try:
            return await self.__storage.load_df(self, columns)  # type: ignore[attr-defined]
        except (RuntimeError, IOError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading dataset of type {self.datatype} "
                f"at location {self.partition_key}/{self.key}"
            ) from e

    def convert(self, dataset: "Dataset", df: pd.DataFrame) -> DataFrameT:
        """Converts loaded pandas Dataframe to @dataframe annotated object using Dataset metadata"""
        try:
            datatype: Type[DataFrameT] = find_dataframe_type(dataset.datatype)
            return datatype._from_df(df)  # type: ignore[attr-defined]
        except KeyError as e:
            raise DatasetConvertError(
                f"Error {type(e).__name__}: {e} converting dataset of type {self.datatype}"
            ) from e

    def adapt(self, datatype: DataFrameT) -> "Dataset[DataFrameT]":
        """Adapts a more generic dataset that contains combined fields to be type specific"""
        return Dataset(
            protocol=self.protocol,
            partition_key=self.partition_key,
            key=self.key,
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",  # type: ignore[attr-defined]
            schema=TypeAdapter(datatype).json_schema(),
        )

    @classmethod
    async def save(cls, dataframe: DataFrameT) -> "Dataset[DataFrameT]":
        return await cls.__storage.save(dataframe)  # type: ignore[attr-defined]

    @classmethod
    async def save_df(
        cls, df: pd.DataFrame, datatype: Type[GenericDataFrameT]
    ) -> "Dataset[GenericDataFrameT]":
        return await cls.__storage.save_df(df, datatype)  # type: ignore[attr-defined]


def find_protocol_impl(qual_type_name: str) -> Type:
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    return datatype


def find_dataframe_type(qual_type_name: str) -> Type[DataFrameT]:
    """Returns dataframe class based on type name used during serialization"""
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    assert hasattr(
        datatype, "__dataframe__"
    ), f"Type {qual_type_name} must be annotated with `@dataframe`."
    return datatype
