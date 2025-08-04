"""Support for `@dataframes` serialization to files"""

from datetime import datetime, timedelta, timezone
from glob import glob
import os
import io
from typing import AsyncGenerator, Generic, Literal, Optional, Type, TypeVar
from uuid import uuid4
from pathlib import Path

import aiofiles
from pydantic import TypeAdapter

try:
    import polars as pl
except ImportError:
    import hopeit.dataframes.polars as pl  # type: ignore  # Polars is optional; set to a mock if not installed

from hopeit.dataframes.dataframe import DataFrameMixin
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import dataclass, dataobject
from hopeit.dataobjects.payload import Payload

DataFrameT = TypeVar("DataFrameT", bound=DataFrameMixin)


@dataobject
@dataclass
class DatasetFileStorageEngineSettings:
    """Pyarrow settings for parquet file storage"""

    compression: Optional[
        Literal["lz4", "uncompressed", "snappy", "gzip", "lzo", "brotli", "zstd"]
    ] = "zstd"
    compression_level: Optional[int] = None
    read_chunk_size: int = 2**20  # 1Mb


class DatasetFileStorage(Generic[DataFrameT]):
    """Support to store dataframes as files,
    using polars parquet format support
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
        database_key: Optional[str],
        group_key: Optional[str],
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
            database_key=database_key,
            group_key=group_key,
            collection=collection,
            save_schema=save_schema,
        )

    async def save_df(
        self,
        df: pl.DataFrame,
        datatype: Type[DataFrameT],
        *,
        partition_dt: Optional[datetime],
        database_key: Optional[str],
        group_key: Optional[str],
        collection: Optional[str],
        save_schema: bool,
    ) -> Dataset:
        """Saves polars df object as parquet to file system
        and returns Dataset metadata to be used when retrieval
        is handled externally
        """
        path = self.path
        partition_key = ""
        if group_key:
            path = path / group_key
        if collection is None:
            collection = datatype.__qualname__.lower()
        path = path / collection
        if self.partition_dateformat:
            partition_key = (partition_dt or datetime.now(tz=timezone.utc)).strftime(
                self.partition_dateformat
            )
            path = path / partition_key
        key = f"{datatype.__qualname__.lower()}_{uuid4().hex}.parquet"

        # Async save parquet file via in-memory buffer
        buf = io.BytesIO()
        df.write_parquet(
            buf,
            compression=self.storage_settings.compression or "zstd",
            compression_level=self.storage_settings.compression_level,
        )
        os.makedirs(path, exist_ok=True)
        path = path / key
        async with aiofiles.open(path, "wb") as f:
            await f.write(buf.getvalue())

        return Dataset(
            protocol=f"{__name__}.{type(self).__name__}",
            partition_key=partition_key,
            key=key,
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",
            partition_dt=partition_dt,
            database_key=database_key,
            group_key=group_key,
            collection=collection,
            schema=TypeAdapter(datatype).json_schema() if save_schema else None,
        )

    async def _get_batch(
        self,
        datatype: Type[DataFrameT],
        *,
        from_partition_dt: datetime,
        to_partition_dt: datetime,
        database_key: Optional[str],
        group_key: Optional[str],
        collection: Optional[str],
    ) -> AsyncGenerator[Dataset, None]:
        """
        Returns a list of Dataset found in a range of partitions
        """
        path = self.path
        partition_key = ""
        if group_key:
            path = path / group_key
        if collection is None:
            collection = datatype.__qualname__.lower()
        path = path / collection

        explored_partitions = set()
        partition_increments = timedelta(days=1)
        partition_dateformat = ""
        partition_comps = []
        if self.partition_dateformat:
            partition_comps = [x for x in self.partition_dateformat.split("/") if len(x)]
            partition_dateformat = "/".join(partition_comps[0 : min(3, len(partition_comps))])
            if len(partition_comps) > 3:
                partition_dateformat += "/" + "/".join(["*" for _ in partition_comps[3:]])

        partition_dt = from_partition_dt
        while partition_dt <= to_partition_dt:
            search_path = path
            if partition_dateformat:
                partition_key = partition_dt.strftime(partition_dateformat)
                search_path = search_path / partition_key

            search_path = search_path / f"{datatype.__qualname__.lower()}*.parquet"

            dir_name = search_path.as_posix()
            if dir_name not in explored_partitions:
                explored_partitions.add(dir_name)
                for entry in glob(dir_name):
                    comps = entry.split("/")
                    yield Dataset(
                        protocol=f"{__name__}.{type(self).__name__}",
                        partition_key="/".join(comps[-len(partition_comps) - 1 : -1]),
                        key=comps[-1],
                        datatype=f"{datatype.__module__}.{datatype.__qualname__}",
                        partition_dt=partition_dt,
                        database_key=database_key,
                        group_key=group_key,
                        collection=collection,
                        schema=None,  # This is a temporary dataset, not intended to be saved
                    )

            partition_dt += partition_increments

    async def load_df(self, dataset: Dataset, columns: Optional[list[str]] = None) -> pl.DataFrame:
        path = self.path
        if dataset.group_key:
            path = path / dataset.group_key
        if dataset.collection:
            path = path / dataset.collection
        if dataset.partition_key:
            path = path / dataset.partition_key
        path = path / dataset.key

        buf = io.BytesIO()
        async with aiofiles.open(path, "rb") as f:
            while True:
                chunk = await f.read(self.storage_settings.read_chunk_size)  # 8 MiB chunks
                if not chunk:  # Do not change this check!
                    break
                buf.write(chunk)
        buf.seek(0)
        return pl.read_parquet(buf, columns=columns)

    def scan_df(self, dataset: Dataset, schema: Optional[pl.Schema] = None) -> pl.LazyFrame:
        path = self.path
        if dataset.group_key:
            path = path / dataset.group_key
        if dataset.collection:
            path = path / dataset.collection
        if dataset.partition_key:
            path = path / dataset.partition_key
        path = path / dataset.key

        return pl.scan_parquet(path, glob=False, schema=schema, extra_columns="ignore")
