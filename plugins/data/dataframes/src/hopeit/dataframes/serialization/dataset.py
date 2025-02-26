"""Dataset objects definition, used as a result of serialized dataframes"""

from typing import Any, Dict, Generic, Optional, Type, TypeVar

from hopeit.dataobjects import dataclass, dataobject, field
import pandas as pd
from pydantic import TypeAdapter

from hopeit.dataframes.setup.registry import get_dataset_storage
from hopeit.dataframes.serialization.protocol import find_dataframe_type

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

    @classmethod
    async def save(
        cls, dataframe: DataFrameT, database_key: str | None = None
    ) -> "Dataset[DataFrameT]":
        storage = await get_dataset_storage(database_key)
        return await storage.save(dataframe)  # type: ignore[attr-defined]

    async def load(self, database_key: str | None = None) -> DataFrameT:
        try:
            storage = await get_dataset_storage(database_key)
            df = await self._load_df(storage)
            return self._convert(df)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading dataset of type {self.datatype} "
                f"at location {self.partition_key}/{self.key}"
            ) from e

    async def _load_df(self, storage: object, columns: Optional[list[str]] = None) -> pd.DataFrame:
        return await storage.load_df(self, columns)  # type: ignore[attr-defined]

    def _convert(self, df: pd.DataFrame) -> DataFrameT:
        """Converts loaded pandas Dataframe to @dataframe annotated object using Dataset metadata"""
        datatype: Type[DataFrameT] = find_dataframe_type(self.datatype)
        return datatype._from_df(df)  # type: ignore[attr-defined]

    def _adapt(self, datatype: DataFrameT) -> "Dataset[DataFrameT]":
        """Adapts a more generic dataset that contains combined fields to be type specific"""
        return Dataset(
            protocol=self.protocol,
            partition_key=self.partition_key,
            key=self.key,
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",  # type: ignore[attr-defined]
            schema=TypeAdapter(datatype).json_schema(),
        )

    @classmethod
    async def _save_df(
        cls, storage: object, df: pd.DataFrame, datatype: Type[GenericDataFrameT]
    ) -> "Dataset[GenericDataFrameT]":
        return await storage.save_df(df, datatype)  # type: ignore[attr-defined]
