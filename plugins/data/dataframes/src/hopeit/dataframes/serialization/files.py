"""Support for `@dataframes` serialization to files"""

import io
from typing import Generic, Optional, Type, TypeVar
from uuid import uuid4

import pandas as pd
from pydantic import TypeAdapter

try:
    import pyarrow  # type: ignore  # noqa  # pylint: disable=unused-import
except ImportError as e:
    raise ImportError(
        "`pyarrow` needs to be installed to use `DatasetFileStorage`",
        "Run `pip install hopeit.dataframes[pyarrow]`",
    ) from e

from hopeit.dataframes.dataframe import DataFrameMixin
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import DataObject
from hopeit.fs_storage import FileStorage

DataFrameT = TypeVar("DataFrameT", bound=DataFrameMixin)


class DatasetFileStorage(Generic[DataFrameT]):
    """Support to store dataframes as files,
    using pandas parquet format support in combination
    with `hopeit.engine` file storage plugins
    """

    def __init__(self, *, location: str, partition_dateformat: Optional[str], **kwargs):
        self.storage: FileStorage = FileStorage(
            path=location, partition_dateformat=partition_dateformat
        )

    async def save(self, dataframe: DataFrameT) -> Dataset:
        """Saves @dataframe annotated object as parquet to file system
        and returns Dataset metadata to be used for retrieval
        """
        datatype = type(dataframe)
        key = f"{datatype.__qualname__.lower()}_{uuid4()}.parquet"
        data = io.BytesIO(
            dataframe._df.to_parquet(  # pylint: disable=protected-access
                engine="pyarrow"
            )
        )
        location = await self.storage.store_file(file_name=key, value=data)
        partition_key = self.storage.partition_key(location)

        return Dataset(
            protocol=f"{__name__}.{type(self).__name__}",
            partition_key=partition_key,
            key=key,
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",
            schema=TypeAdapter(datatype).json_schema(),
        )

    async def save_df(self, df: pd.DataFrame, datatype: Type[DataObject]) -> Dataset:
        """Saves pandas df object as parquet to file system
        and returns Dataset metadata to be used when retrieval
        is handled externally
        """
        key = f"{datatype.__qualname__.lower()}_{uuid4()}.parquet"
        data = io.BytesIO(
            df.to_parquet(  # pylint: disable=protected-access
                engine="pyarrow"
            )
        )
        location = await self.storage.store_file(file_name=key, value=data)
        partition_key = self.storage.partition_key(location)

        return Dataset(
            protocol=f"{__name__}.{type(self).__name__}",
            partition_key=partition_key,
            key=key,
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",
            schema=TypeAdapter(datatype).json_schema(),
        )

    async def load_df(self, dataset: Dataset, columns: Optional[list[str]] = None) -> pd.DataFrame:
        data = await self.storage.get_file(dataset.key, partition_key=dataset.partition_key)
        if data is None:
            raise FileNotFoundError(dataset.key)
        return pd.read_parquet(io.BytesIO(data), engine="pyarrow", columns=columns)
