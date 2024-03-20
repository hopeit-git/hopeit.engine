"""
DataFrames type abstractions.

Example:

    from hopeit.dataobjects import dataclass # equivalent to `dataclasses.dataclass`
    from hopeit.dataframes import dataframe

    @dataframe
    @dataclass
    class MyObject:
        name: str
        number: int
"""

from dataclasses import Field, asdict, dataclass, fields, make_dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, Generic, Iterator, List, Optional, Type, TypeVar

import numpy as np
import pandas as pd
from dataclasses_jsonschema import JsonSchemaMixin
from hopeit.dataobjects import (
    DataObject,
    StreamEventMixin,
    StreamEventParams,
    dataobject,
)

DataFrameT = TypeVar("DataFrameT")


@dataclass
class DataFrameMetadata(Generic[DataObject]):
    columns: List[str]
    fields: Dict[str, Field]
    serialized_type: Type[DataObject]


@dataclass
class DataFrameParams:
    """
    Helper class used to access attributes in @dataframe
    decorated objects, based on dot notation expressions
    """

    datatypes: Optional[str]

    @staticmethod
    def extract_attr(obj, expr):
        value = obj
        for attr_name in expr.split("."):
            if value:
                value = getattr(value, attr_name)
        return value


class DataFrameMixin(Generic[DataFrameT, DataObject]):
    """
    MixIn class to add functionality for DataFrames dataobjects

    Do not use this class directly, instead use `@dataframe` class decorator.
    """

    DATATYPE_MAPPING = {
        int: lambda x: x.astype(np.int64),
        float: lambda x: x.astype(np.float64),
        str: lambda x: x.astype(object),
        date: pd.to_datetime,
        datetime: pd.to_datetime,
    }

    def __init__(self) -> None:
        # Fields added here only to allow mypy to provide correct type hints
        self.__data_object__: Dict[str, Any] = {}
        self.__dataframe__: DataFrameMetadata = None  # type: ignore
        self.__df = pd.DataFrame()
        raise NotImplementedError  # must use @dataframe decorator  # pragma: no cover

    @staticmethod
    def __init_from_series__(
        self, **series: pd.Series
    ):  # pylint: disable=bad-staticmethod-argument
        if self.__data_object__["validate"]:
            series = self._coerce_datatypes(series)
        df = pd.DataFrame(series)
        setattr(self, "__df", df[self.__dataframe__.columns])

    @classmethod
    def _from_df(cls, df: pd.DataFrame, **series: Any) -> DataFrameT:
        df = df if cls.__data_object__["unsafe"] else pd.DataFrame(df)
        obj = cls(**{**df._series, **series})  # pylint: disable=protected-access
        return obj  # type: ignore

    @classmethod
    def _from_array(cls, array: np.ndarray) -> DataFrameT:
        return cls._from_df(pd.DataFrame(array, columns=cls.__dataframe__.columns))

    @classmethod
    def _from_dataobjects(cls, items: Iterator[DataObject]) -> DataFrameT:
        return cls._from_df(pd.DataFrame(asdict(item) for item in items))  # type: ignore

    @classmethod
    def _from_df_unsafe(cls, df: pd.DataFrame, **series: pd.Series) -> DataFrameT:
        for col, values in series.items():
            df[col] = values
        obj = cls(**df._series)  # pylint: disable=protected-access
        return obj  # type: ignore

    @property
    def _df(self) -> pd.DataFrame:
        return getattr(self, "__df")

    def __getitem__(self, key) -> "DataFrameT":
        return self._from_df(self.__df[key])

    def _to_dataobjects(self) -> List[DataObject]:
        return [
            self.__dataframe__.serialized_type(**fields)
            for fields in self.__df.to_dict(orient="records")
        ]

    def to_json(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "Dataframe must be used inside `@dataobject(unsafe=True)` to be used as an output"
        )

    def to_dict(self, *args, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError(
            "Dataframe must be used inside `@dataobject(unsafe=True)` to be used as an output"
        )

    @classmethod
    def from_json(cls, *args, **kwargs) -> DataObject:
        return cls.__dataframe__.serialized_type.from_dict(*args, **kwargs)

    @classmethod
    def from_dict(
        cls,
        *args,
        **kwargs,
    ) -> DataObject:
        return cls.__dataframe__.serialized_type.from_dict(*args, **kwargs)

    @classmethod
    def json_schema(cls, *args, **kwargs) -> Dict[str, Any]:
        if cls.__data_object__["schema"]:
            schema = cls.__dataframe__.serialized_type.json_schema(*args, **kwargs)
            schema[cls.__name__] = schema[cls.__dataframe__.serialized_type.__name__]
            return schema
        return {}

    def event_id(self, *args, **kwargs) -> str:
        return ""

    def event_ts(self, *args, **kwargs) -> datetime:
        return datetime.now(tz=timezone.utc)

    def __getattribute__(self, name: str) -> Any:
        if name[:2] == "__":
            return object.__getattribute__(self, name)
        if name in self.__dataframe__.columns:
            return self.__df[name]
        if name[:15] == "_DataFrameMixin":
            return object.__getattribute__(self, name[15:])
        return object.__getattribute__(self, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__dataframe__.columns:
            self.__df[name] = value
        else:
            object.__setattr__(self, name, value)

    def _coerce_datatypes(self, series: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        return {
            name: self.DATATYPE_MAPPING[field.type](series[name])  # type: ignore
            for name, field in self.__dataframe__.fields.items()
        }


def dataframe(
    decorated_class=None,
    unsafe: bool = False,
    validate: bool = True,
    schema: bool = True,
) -> Callable[[Type], Type[DataFrameMixin]]:
    """
    Decorator for dataclasses intended to be used as dataframes.
    """

    def add_dataframe_mixin(cls) -> Type[DataFrameMixin]:
        if hasattr(cls, "__annotations__") and hasattr(cls, "__dataclass_fields__"):
            amended_class = type(
                cls.__name__,
                (DataFrameMixin, JsonSchemaMixin) + cls.__mro__,
                dict(cls.__dict__),
            )
            setattr(amended_class, "__init__", DataFrameMixin.__init_from_series__)
            return amended_class
        return cls

    def add_dataframe_metadata(cls):
        serialized_fiels = [(field.name, field.type) for field in fields(cls)]
        serialized_type = make_dataclass(cls.__name__ + "_", serialized_fiels)
        serialized_type = dataobject(serialized_type, unsafe=True)

        setattr(
            cls,
            "__dataframe__",
            DataFrameMetadata(
                columns=[field.name for field in fields(cls)],
                fields={field.name: field for field in fields(cls)},
                serialized_type=serialized_type,
            ),
        )

    def add_dataobject_annotations(cls, unsafe: bool, validate: bool, schema: bool):
        setattr(
            cls,
            "__data_object__",
            {"unsafe": unsafe, "validate": validate, "schema": schema},
        )
        setattr(cls, "__stream_event__", StreamEventParams(None, None))
        setattr(cls, "event_id", StreamEventMixin.event_id)
        setattr(cls, "event_ts", StreamEventMixin.event_ts)

    def set_fields_optional(cls):
        for field in fields(cls):
            field.default = None

    def wrap(cls) -> Type[DataFrameMixin]:
        if hasattr(cls, "__dataframe__"):
            return cls
        amended_class = add_dataframe_mixin(cls)
        add_dataframe_metadata(amended_class)
        add_dataobject_annotations(amended_class, unsafe, validate, schema)
        set_fields_optional(amended_class)
        return amended_class

    if decorated_class is None:
        return wrap
    return wrap(decorated_class)  # type: ignore
