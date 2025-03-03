"""Support for `@dataframes` serialization to files"""

from datetime import UTC, datetime
import io
from typing import Generic, Literal, Optional, Type, TypeVar
from uuid import uuid4
from pathlib import Path

import aiofiles
import aiofiles.os
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
from hopeit.dataobjects import dataclass, dataobject
from hopeit.dataobjects.payload import Payload

DataFrameT = TypeVar("DataFrameT", bound=DataFrameMixin)


@dataobject
@dataclass
class DatasetFileStorageEngineSettings:
    """Pyarrow settings for parquet file storage"""

    compression: Literal["snappy", "gzip", "brotli", "lz4", "zstd"] | None = None
    compression_level: int | str | None = None


class DatasetFileStorage(Generic[DataFrameT]):
    """Support to store dataframes as files,
    using pandas parquet format support in combination
    with `hopeit.engine` file storage plugins
    """

    def __init__(
        self,
        *,
        location: str,
        partition_dateformat: Optional[str],
        storage_settings: dict[str, str | int],
        **kwargs,  # Needed to support other storage implementations
    ):
        self.path = Path(location)
        self.partition_dateformat = partition_dateformat
        self.storage_settings: DatasetFileStorageEngineSettings = Payload.from_obj(
            storage_settings, DatasetFileStorageEngineSettings
        )

    async def save(
        self,
        dataframe: DataFrameT,
        *,
        partition_dt: Optional[datetime],
        collection: Optional[str],
        save_schema: bool,
    ) -> Dataset:
        """Saves @dataframe annotated object as parquet to file system
        and returns Dataset metadata to be used for retrieval
        """
        datatype: Type[DataFrameT] = type(dataframe)
        return await self.save_df(
            dataframe._df,
            datatype,
            partition_dt=partition_dt,
            collection=collection,
            save_schema=save_schema,
        )

    async def save_df(
        self,
        df: pd.DataFrame,
        datatype: Type[DataFrameT],
        *,
        partition_dt: Optional[datetime],
        collection: Optional[str],
        save_schema: bool,
    ) -> Dataset:
        """Saves pandas df object as parquet to file system
        and returns Dataset metadata to be used when retrieval
        is handled externally
        """
        path = self.path
        partition_key = ""
        if collection is None:
            collection = datatype.__qualname__.lower()
        path = path / collection
        if self.partition_dateformat:
            partition_key = (partition_dt or datetime.now(tz=UTC)).strftime(
                self.partition_dateformat
            )
            path = path / partition_key
        key = f"{datatype.__qualname__.lower()}_{uuid4().hex}.parquet"

        # Async save parquet file
        await aiofiles.os.makedirs(path, exist_ok=True)
        path = path / key

        async with aiofiles.open(path, "wb") as f:
            await f.write(
                df.to_parquet(
                    engine="pyarrow",
                    compression=self.storage_settings.compression,
                    compression_level=self.storage_settings.compression_level,
                )
            )

        return Dataset(
            protocol=f"{__name__}.{type(self).__name__}",
            partition_key=partition_key,
            key=key,
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",
            partition_dt=partition_dt,
            collection=collection,
            schema=TypeAdapter(datatype).json_schema() if save_schema else None,
        )

    async def load_df(self, dataset: Dataset, columns: Optional[list[str]] = None) -> pd.DataFrame:
        path = self.path
        if dataset.collection:
            path = path / dataset.collection
        if dataset.partition_key:
            path = path / dataset.partition_key
        path = path / dataset.key

        # Async load parquet into pandas dataframe
        async with aiofiles.open(path, "rb") as f:
            return pd.read_parquet(io.BytesIO(await f.read()), engine="pyarrow", columns=columns)
