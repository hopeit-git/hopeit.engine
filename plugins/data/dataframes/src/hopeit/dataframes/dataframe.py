"""
DataFrames type abstractions.
"""

import dataclasses
from datetime import date, datetime, timezone
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

try:
    import polars as pl
except ImportError:
    import hopeit.dataframes.polars as pl  # type: ignore  # Polars is optional; set to a mock if not installed

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
    schema: Optional[pl.Schema]


# Validation
def not_null_check(series: pl.Series) -> bool:
    return series.null_count() == 0


class DataTypeMapping:
    mapping: Dict[Type, Tuple[Optional["pl.DataType"], Tuple[Callable, ...]]] = {
        int: (None, ()),
        bool: (None, ()),
        float: (None, ()),
        str: (None, ()),
        date: (None, ()),
        datetime: (None, ()),
        Union[int, None]: (None, ()),  # type: ignore[dict-item]
        Union[bool, None]: (None, ()),  # type: ignore[dict-item]
        Union[float, None]: (None, ()),  # type: ignore[dict-item]
        Union[str, None]: (None, ()),  # type: ignore[dict-item]
        Union[date, None]: (None, ()),  # type: ignore[dict-item]
        Union[datetime, None]: (None, ()),  # type: ignore[dict-item]
    }

    @classmethod
    def lazy_init(cls):
        cls.mapping = {
            int: (pl.Int64(), (not_null_check,)),
            bool: (pl.Boolean(), (not_null_check,)),
            float: (pl.Float64(), (not_null_check,)),
            str: (pl.String(), (not_null_check,)),
            date: (pl.Date(), (not_null_check,)),
            datetime: (pl.Datetime(time_unit="us", time_zone=timezone.utc), (not_null_check,)),
            Union[int, None]: (pl.Int64(), ()),
            Union[bool, None]: (pl.Boolean(), ()),
            Union[float, None]: (pl.Float64(), ()),
            Union[str, None]: (pl.String(), ()),
            Union[date, None]: (pl.Date(), ()),
            Union[datetime, None]: (pl.Datetime(time_unit="us", time_zone=timezone.utc), ()),
        }

    @classmethod
    def get_validators(cls, field_type: Type) -> Tuple[Callable, ...]:
        entry = cls.mapping.get(field_type)
        if entry:
            return entry[1]
        return ()

    @classmethod
    def get_schema_type(cls, field_type: Type) -> Optional["pl.DataType"]:
        entry = cls.mapping.get(field_type)
        if entry:
            return entry[0]
        # Enum fields in datablocks
        if issubclass(field_type, str):
            entry = cls.mapping.get(str)
        elif issubclass(field_type, int):
            entry = cls.mapping.get(int)
        if entry:
            return entry[0]
        return None


if not hasattr(pl, "HOPEIT_DATAFRAMES_POLARS_IS_MOCK"):
    DataTypeMapping.lazy_init()


class DataFrameMixin(Generic[DataFrameT, DataObject]):
    """
    MixIn class to add functionality for DataFrames dataobjects

    Do not use this class directly, instead use `@dataframe` class decorator.
    """

    DataFrameValueType = Union[int, bool, float, str, date, datetime, None]

    def __init__(self, **series: pl.Series) -> None:
        # Fields added here only to allow mypy to provide correct type hints
        self.__data_object__: Dict[str, Any] = {}
        self.__dataframe__: DataFrameMetadata = None  # type: ignore
        self.__df = pl.DataFrame()
        raise NotImplementedError  # must use @dataframe decorator  # pragma: no cover

    @staticmethod
    def __init_from_series__(self, **series: pl.Series) -> None:  # pylint: disable=bad-staticmethod-argument
        validate: bool = self.__data_object__["validate"]

        # Assign default values for missing fields
        max_len: int | None = None
        for field_name, field_info in self.__dataframe__.fields.items():
            if series.get(field_name) is None:
                max_len = max_len or max(len(data) for data in series.values() if data is not None)
                default_value = field_info.get_default()
                if default_value is not PydanticUndefined:
                    series[field_name] = pl.Series(
                        name=field_name, values=[default_value] * (max_len or 1)
                    )
                else:
                    series[field_name] = None  # type: ignore[assignment]

        # Create dataframe using schema columns only
        df = pl.DataFrame(
            {col: data for col, data in series.items() if col in self.__dataframe__.columns},
            schema=self.__dataframe__.schema if validate else None,
        )

        # Validate (i.e. not nullable fields)
        if validate:
            for field_name, field_info in self.__dataframe__.fields.items():
                for func in DataTypeMapping.get_validators(field_info.annotation):
                    if not func(df[field_name]):
                        raise TypeError(
                            f"{type(self).__name__} validation failed for field: {field_name}: {func.__name__}"
                        )

        setattr(self, "__df", df[self.__dataframe__.columns])

    @classmethod
    def _from_df(cls, df: pl.DataFrame, **series: Any) -> DataFrameT:
        df_series = {series.name: series for series in df}
        obj = cls(**{**df_series, **series})
        return obj  # type: ignore

    @classmethod
    def _from_dataobjects(cls, items: Iterator[DataObject]) -> DataFrameT:
        return cls._from_df(pl.DataFrame(Payload.to_obj(item) for item in items))  # type: ignore[misc]

    @property
    def _df(self) -> pl.DataFrame:
        return getattr(self, "__df")

    def __getitem__(self, key) -> "DataFrameT":
        return self._from_df(self.__df[key])

    def _to_dataobjects(self) -> List[DataObject]:
        return [Payload.from_obj(obj, datatype=self.DataObject) for obj in self.__df.to_dicts()]

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
        df: pl.DataFrame,
        field_name: str,
        field_info: FieldInfo,
    ) -> pl.Series:
        try:
            return df[field_name]
        except KeyError:
            default_value = field_info.get_default()
            if default_value is not PydanticUndefined:
                return pl.Series(name=field_name, values=[default_value] * len(df))
            raise


def dataframe(
    decorated_class=None,
    unsafe: bool = False,
    validate: bool = True,
    schema: bool = True,
) -> Callable[[Type], Type[DataFrameMixin]]:
    """
    Decorator for dataclasses intended to be used as dataframes.
    """

    def get_dataframe_schema(cls) -> pl.Schema:
        schema_fields: dict[str, pl.DataType] = {}
        for field_name, field_info in fields(cls).items():  # type: ignore[type-var]
            datatype = DataTypeMapping.get_schema_type(field_info.annotation)  # type: ignore[arg-type]
            if datatype is None:
                raise TypeError(
                    f"{cls.__name__}: Unsupported type for field {field_name}: {field_info.annotation}"
                )
            schema_fields[field_name] = datatype
        return pl.Schema(schema_fields)

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

    def add_dataframe_metadata(cls) -> None:
        serialized_fields = {k: (v.annotation, v) for k, v in fields(cls).items()}
        dataobject_name = str(cls.__name__) + "DataObject"
        dataobject_type = create_model(dataobject_name, **serialized_fields)  # type: ignore[call-overload]
        dataobject_type = dataobject(dataobject_type, unsafe=True)

        setattr(cls, "DataObject", dataobject_type)
        setattr(
            cls,
            "__dataframe__",
            DataFrameMetadata(
                columns=list(fields(cls).keys()),
                fields=dict(fields(cls).items()),
                schema=None if pl is None else get_dataframe_schema(cls),
            ),
        )

    def add_dataobject_annotations(cls, unsafe: bool, validate: bool, schema: bool) -> None:
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
