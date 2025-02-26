from importlib import import_module
from typing import Type, TypeVar

DataFrameT = TypeVar("DataFrameT")


def find_protocol_impl(qual_type_name: str) -> Type:
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    return datatype


def find_dataframe_type(qual_type_name: str) -> Type[DataFrameT]:
    """Returns dataframe class based on type name used during serialization"""
    mod_name, type_name = (
        ".".join(qual_type_name.split(".")[:-1]),
        qual_type_name.split(".")[-1],
    )
    module = import_module(mod_name)
    datatype = getattr(module, type_name)
    assert hasattr(datatype, "__dataframe__"), (
        f"Type {qual_type_name} must be annotated with `@dataframe`."
    )
    return datatype
