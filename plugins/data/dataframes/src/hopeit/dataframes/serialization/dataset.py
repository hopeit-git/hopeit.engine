"""Dataset objects definition, used as a result of serialized dataframes
"""

from importlib import import_module
from typing import Type, TypeVar

from hopeit.dataobjects import dataclass, dataobject

DataFrameT = TypeVar("DataFrameT")


@dataobject
@dataclass
class Dataset:
    protocol: str
    partition_key: str
    key: str
    datatype: str


def find_protocol_impl(qual_type_name: str) -> Type:
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    return datatype
