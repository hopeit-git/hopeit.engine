"""Support for `@dataframes` serialization to files
"""

import io
from importlib import import_module
from typing import Callable, Generic, Optional, Type, TypeVar, Union
from uuid import uuid4

import pandas as pd

try:
    import pyarrow  # type: ignore  # noqa  # pylint: disable=unused-import
except ImportError as e:
    raise ImportError(
        "`pyarrow` needs to be installed to use `DatasetFileStorage`",
        "Run `pip install hopeit.dataframes[pyarrow]`",
    ) from e

from hopeit.dataframes.dataframe import DataFrameMixin
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import EventPayloadType
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
        )

    async def load(self, dataset: Dataset) -> EventPayloadType:
        """Loads @dataframe annotated object using Dataset metadata"""
        datatype: Type[DataFrameT] = find_dataframe_type(dataset.datatype)
        data = await self.storage.get_file(
            dataset.key, partition_key=dataset.partition_key
        )
        if data is None:
            raise FileNotFoundError(dataset.key)
        df = pd.read_parquet(io.BytesIO(data), engine="pyarrow")
        return datatype._from_df(df)  # pylint: disable=protected-access

    async def ser_wrapper(
        self,
        base_serialization: Callable,
        data: Union[EventPayloadType, DataFrameT],
        level: int,
    ) -> bytes:
        """Serialization wrapper that plugins-in into hopeit.engine
        serialization when dataframes plugin is initialized
        """
        if hasattr(data, "__dataframeobject__"):
            data = await data._serialize()  # type: ignore  # pylint: disable=protected-access
        if hasattr(data, "__dataframe__"):
            data = await self.save(data)  # type: ignore
        return await base_serialization(data, level)

    async def deser_wrapper(
        self,
        base_deserialization: Callable,
        data: bytes,
        datatype: Union[Type[EventPayloadType], Type[DataFrameT]],
    ) -> Union[EventPayloadType, DataFrameT]:
        """Deerialization wrapper that plugins-in into hopeit.engine
        deserialization when dataframes plugin is initialized
        """
        if hasattr(datatype, "__dataframeobject__"):
            dataset = await base_deserialization(
                data, datatype.__dataframeobject__.serialized_type  # type: ignore
            )
            return await datatype._deserialize(dataset)  # type: ignore  # pylint: disable=protected-access
        if hasattr(datatype, "__dataframe__"):
            dataset = await base_deserialization(data, Dataset)
            return await self.load(dataset)
        return await base_deserialization(data, datatype)


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
