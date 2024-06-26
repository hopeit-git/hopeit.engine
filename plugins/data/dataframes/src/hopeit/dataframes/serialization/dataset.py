"""Dataset objects definition, used as a result of serialized dataframes
"""

from importlib import import_module
from typing import Generic, Type, TypeVar

from hopeit.dataobjects import dataclass, dataobject

DataFrameT = TypeVar("DataFrameT")


@dataobject
@dataclass
class Dataset(Generic[DataFrameT]):
    """Persisted representation of a @dataframe object"""
    protocol: str
    partition_key: str
    key: str
    datatype: str

    async def load(self) -> DataFrameT:
        return await self.__storage.load(self)  # type: ignore[attr-defined]

    @classmethod
    async def save(cls, dataframe: DataFrameT) -> "Dataset[DataFrameT]":
        return await cls.__storage.save(dataframe)  # type: ignore[attr-defined]


def find_protocol_impl(qual_type_name: str) -> Type:
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    return datatype
