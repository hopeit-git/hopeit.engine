"""
DataFrames type abstractions.
"""

import dataclasses
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, Generic, Iterator, List, Type, TypeVar, Union

import numpy as np
import pandas as pd
from pydantic import create_model
from pydantic.fields import FieldInfo

from hopeit.dataobjects import (
    DataObject,
    StreamEventMixin,
    StreamEventParams,
    dataobject,
    fields,
)
from hopeit.dataobjects.payload import Payload
from pydantic_core import PydanticUndefined

DataFrameT = TypeVar("DataFrameT")


@dataclasses.dataclass
class DataFrameMetadata:
    columns: List[str]
    fields: Dict[str, FieldInfo]


# Functions to do type coercion
def _series_to_int(field_name: str, x: pd.Series) -> pd.Series:
    if x.isnull().values.any():  # type: ignore[union-attr]
        raise ValueError(f"Field `{field_name}` is not nullable")
    return x.astype(np.int64)


def _series_to_bool(field_name: str, x: pd.Series) -> pd.Series:
    if x.isnull().values.any():  # type: ignore[union-attr]
        raise ValueError(f"Field `{field_name}` is not nullable")
    return x.astype(bool)


def _series_to_float(field_name: str, x: pd.Series) -> pd.Series:
    if x.isnull().values.any():  # type: ignore[union-attr]
        raise ValueError(f"Field `{field_name}` is not nullable")
    return x.astype(np.float64)


def _series_to_str(field_name: str, x: pd.Series) -> pd.Series:
    if x.isnull().values.any():  # type: ignore[union-attr]
        raise ValueError(f"Field `{field_name}` is not nullable")
    return x.astype(str)


# Functions to do type coercion
def _series_to_int_nullable(_field_name: str, x: pd.Series) -> pd.Series:
    return x.dropna().astype(np.int64)


def _series_to_bool_nullable(_field_name: str, x: pd.Series) -> pd.Series:
    return x.dropna().astype(bool)


def _series_to_float_nullable(_field_name: str, x: pd.Series) -> pd.Series:
    return x.dropna().astype(np.float64)


def _series_to_str_nullable(_field_name: str, x: pd.Series) -> pd.Series:
    return x.dropna().astype(str)


def _series_to_datetime(field_name: str, x: pd.Series) -> pd.Series:
    if x.isnull().values.any():  # type: ignore[union-attr]
        raise ValueError(f"Field `{field_name}` is not nullable")
    return pd.to_datetime(x)


def _series_to_utc_datetime(field_name: str, x: pd.Series) -> pd.Series:
    if x.isnull().values.any():  # type: ignore[union-attr]
        raise ValueError(f"Field `{field_name}` is not nullable")
    return pd.to_datetime(x, utc=True)


def _series_to_datetime_nullable(_field_name: str, x: pd.Series) -> pd.Series:
    return pd.to_datetime(x.dropna())


def _series_to_utc_datetime_nullable(_field_name: str, x: pd.Series) -> pd.Series:
    return pd.to_datetime(x.dropna(), utc=True)


class DataFrameMixin(Generic[DataFrameT, DataObject]):
    """
    MixIn class to add functionality for DataFrames dataobjects

    Do not use this class directly, instead use `@dataframe` class decorator.
    """

    DataFrameValueType = Union[int, bool, float, str, date, datetime, None]

    DATATYPE_MAPPING = {
        int: _series_to_int,
        bool: _series_to_bool,
        float: _series_to_float,
        str: _series_to_str,
        date: _series_to_datetime,
        datetime: _series_to_utc_datetime,
        Union[int, None]: _series_to_int_nullable,
        Union[bool, None]: _series_to_bool_nullable,
        Union[float, None]: _series_to_float_nullable,
        Union[str, None]: _series_to_str_nullable,
        Union[date, None]: _series_to_datetime_nullable,
        Union[datetime, None]: _series_to_utc_datetime_nullable,
    }

    def __init__(self, **series: pd.Series) -> None:
        # Fields added here only to allow mypy to provide correct type hints
        self.__data_object__: Dict[str, Any] = {}
        self.__dataframe__: DataFrameMetadata = None  # type: ignore
        self.__df = pd.DataFrame()
        raise NotImplementedError  # must use @dataframe decorator  # pragma: no cover

    @staticmethod
    def __init_from_series__(self, **series: pd.Series):  # pylint: disable=bad-staticmethod-argument
        df = pd.DataFrame(series)
        df.index.name = None  # Removes index name to avoid colisions with series name
        if self.__data_object__["validate"]:
            df = pd.DataFrame(self._coerce_datatypes(df))
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
        return cls._from_df(pd.DataFrame(Payload.to_obj(item) for item in items))  # type: ignore[misc]

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

    def _normalize_null_values(
        self, value: Union[DataFrameValueType, pd.Timestamp]
    ) -> DataFrameValueType:
        return None if pd.isnull(value) else value

    def _to_dataobjects(self, normalize_null_values: bool) -> List[DataObject]:
        if normalize_null_values:
            return [
                self.DataObject(**{k: self._normalize_null_values(v) for k, v in fields.items()})
                for fields in self.__df.to_dict(orient="records")
            ]
        return [self.DataObject(**fields) for fields in self.__df.to_dict(orient="records")]

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

    def _get_series(
        self,
        df: pd.DataFrame,
        field_name: str,
        field_info: FieldInfo,
    ) -> pd.Series:
        try:
            return df[field_name]
        except KeyError:
            default_value = field_info.get_default()
            if default_value is not PydanticUndefined:
                return pd.Series([default_value] * len(df))
            raise

    def _coerce_datatypes(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, pd.Series]:
        return {
            name: self.DATATYPE_MAPPING[field.annotation](  # type: ignore[index, operator]
                name, self._get_series(df, name, field)
            )
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
                (DataFrameMixin,) + cls.__mro__,
                dict(cls.__dict__),
            )
            setattr(amended_class, "__init__", DataFrameMixin.__init_from_series__)
            return amended_class
        return cls

    def add_dataframe_metadata(cls):
        serialized_fields = {k: (v.annotation, v) for k, v in fields(cls).items()}
        dataobject_type = create_model(cls.__name__ + "DataObject", **serialized_fields)
        dataobject_type = dataobject(dataobject_type, unsafe=True)

        setattr(cls, "DataObject", dataobject_type)
        setattr(
            cls,
            "__dataframe__",
            DataFrameMetadata(
                columns=list(fields(cls).keys()),
                fields=dict(fields(cls).items()),
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

    def wrap(cls) -> Type[DataFrameMixin]:
        if hasattr(cls, "__dataframe__"):
            return cls
        add_dataframe_metadata(cls)
        amended_class = add_dataframe_mixin(cls)
        add_dataobject_annotations(amended_class, unsafe, validate, schema)
        return amended_class

    if decorated_class is None:
        return wrap
    return wrap(decorated_class)  # type: ignore
