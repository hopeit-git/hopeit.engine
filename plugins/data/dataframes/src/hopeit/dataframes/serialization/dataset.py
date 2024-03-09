from importlib import import_module
from typing import Any, Generic, List, Type, TypeVar

from hopeit.dataobjects import DataObject, dataclass, dataobject

DataFrameType = TypeVar("DataFrameType")


@dataobject
@dataclass
class Dataset:
    protocol: str
    location: str
    datatype: str


def find_protocol_impl(qual_type_name: str) -> Type:
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    return datatype
