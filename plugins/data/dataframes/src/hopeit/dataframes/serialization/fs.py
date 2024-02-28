from datetime import datetime, timezone
import io
from importlib import import_module
import os
from pathlib import Path
from typing import Callable, Generic, Optional, Type, TypeVar, Union
from uuid import uuid4

import aiofiles
import pandas as pd
from hopeit.dataframes import serialization
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import DataObject, EventPayloadType
from hopeit.dataobjects.payload import Payload

DataFrameType = TypeVar("DataFrameType")


class DatasetFsStorage(Generic[DataFrameType]):

    def __init__(self, *, location: str, partition_dateformat: Optional[str], **kwargs):
        self.base_path = Path(location)
        self.partition_dateformat = partition_dateformat or "%Y/%m/%d/%H/"

    async def save(self, dataframe: DataFrameType) -> Dataset:
        datatype = type(dataframe)
        path = self.base_path / _get_partition_key(self.partition_dateformat)
        os.makedirs(path.resolve().as_posix(), exist_ok=True)
        location = path / f"{datatype.__qualname__.lower()}_{uuid4()}.parquet"
        async with aiofiles.open(location, "wb") as f:
            await f.write(dataframe.df.to_parquet(engine="pyarrow"))

        dataset = Dataset(
            protocol=f"{__name__}.DatasetFsStorage",
            location=location.as_posix(),
            datatype=f"{datatype.__module__}.{datatype.__qualname__}",
        )
        setattr(dataframe, "__dataset", dataset)
        return dataset

    @staticmethod
    async def load(dataset: Dataset) -> DataFrameType:
        datatype = find_dataframe_type(dataset.datatype)
        async with aiofiles.open(dataset.location, "rb") as f:
            df = pd.read_parquet(io.BytesIO(await f.read()), engine="pyarrow")
            return datatype.from_df(df)

    async def ser_wrapper(
        self,
        base_serialization: Callable,
        data: Union[EventPayloadType, DataFrameType],
        level: int,
    ) -> bytes:
        if hasattr(data, "__dataframeobject__"):
            data = await data.serialize()
        if hasattr(data, "__dataframe__"):
            data = await self.save(data)
        return await base_serialization(data, level)

    async def deser_wrapper(
        self,
        base_deserialization: Callable,
        data: bytes,
        datatype: Type[EventPayloadType],
    ) -> EventPayloadType:
        if hasattr(datatype, "__dataframeobject__"):
            dataset = await base_deserialization(
                data, datatype.__dataframeobject__.serialized_type
            )
            return await datatype.deserialize(dataset)
        if hasattr(datatype, "__dataframe__"):
            dataset = await base_deserialization(data, Dataset)
            return await self.load(dataset)
        return await base_deserialization(data, datatype)


def find_dataframe_type(qual_type_name: str) -> Type[DataFrameType]:
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


def _get_partition_key(partition_dateformat: str) -> str:
    return datetime.now(tz=timezone.utc).strftime(partition_dateformat.strip('/')) + '/'
