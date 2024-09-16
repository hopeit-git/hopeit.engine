"""Dataset objects definition, used as a result of serialized dataframes"""

from importlib import import_module
from typing import Any, Dict, Generic, Type, TypeVar

from hopeit.dataobjects import dataclass, dataobject, field

DataFrameT = TypeVar("DataFrameT")


class DatasetLoadError(Exception):
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
            dataframe = await self.__storage.load(self)  # type: ignore[attr-defined]
            return dataframe
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading dataset of type {self.datatype} "
                f"at location {self.partition_key}/{self.key}"
            ) from e

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
