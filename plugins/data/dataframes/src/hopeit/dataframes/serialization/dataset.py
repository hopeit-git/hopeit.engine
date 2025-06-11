"""Dataset objects definition, used as a result of serialized dataframes"""

from datetime import datetime
from typing import Any, Dict, Generic, Optional, Type, TypeVar

from hopeit.dataobjects import dataclass, dataobject
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
    partition_dt: Optional[datetime] = None
    database_key: Optional[str] = None
    group_key: Optional[str] = None
    collection: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None

    @classmethod
    async def save(
        cls,
        dataframe: DataFrameT,
        *,
        partition_dt: Optional[datetime] = None,
        database_key: Optional[str] = None,
        group_key: Optional[str] = None,
        collection: Optional[str] = None,
        save_schema: bool = False,
    ) -> "Dataset[DataFrameT]":
        storage = await get_dataset_storage(database_key)
        return await storage.save(  # type: ignore[attr-defined]
            dataframe,
            partition_dt=partition_dt,
            database_key=database_key,
            group_key=group_key,
            collection=collection,
            save_schema=save_schema,
        )

    @classmethod
    async def load(
        cls,
        dataset: "Dataset[DataFrameT]",
        database_key: Optional[str] = None,
    ) -> DataFrameT:
        try:
            storage = await get_dataset_storage(database_key)
            df = await dataset._load_df(storage)
            return dataset._convert(df)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading dataset of type {dataset.datatype} "
                f"at location {dataset.partition_key}/{dataset.key}"
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
            partition_dt=self.partition_dt,
            database_key=self.database_key,
            group_key=self.group_key,
            collection=self.collection,
            schema=TypeAdapter(datatype).json_schema() if self.schema else None,
        )

    @classmethod
    async def _save_df(
        cls,
        storage: object,
        df: pd.DataFrame,
        datatype: Type[GenericDataFrameT],
        *,
        partition_dt: Optional[datetime],
        database_key: Optional[str],
        group_key: Optional[str],
        collection: Optional[str],
        save_schema: bool,
    ) -> "Dataset[GenericDataFrameT]":
        return await storage.save_df(  # type: ignore[attr-defined]
            df,
            datatype,
            partition_dt=partition_dt,
            database_key=database_key,
            group_key=group_key,
            collection=collection,
            save_schema=save_schema,
        )
