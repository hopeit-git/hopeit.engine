"""
`@dataframeobject` annonation mixin to serialize a group of `@dataframe`s.

Datasets behaves as DataObject so they can be used as payload
for endpoints and streams.
"""

from dataclasses import Field, dataclass, fields, make_dataclass
from types import NoneType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import (
    DataObject,
    StreamEventMixin,
    StreamEventParams,
    dataobject,
)

DataFrameObjectType = TypeVar("DataFrameObjectType")


@dataclass
class DataframeObjectMetadata(Generic[DataObject]):
    serialized_type: Type[DataObject]


class DataframeObjectMixin(Generic[DataFrameObjectType]):
    """
    MixIn class to add functionality for `@dataframeobject`s

    Do not use this class directly, instead use `@dataframeobject` class decorator.
    """

    __storage: ClassVar[Any] = None

    def __init__(self) -> None:
        self.__dataframeobject__: DataframeObjectMetadata = None  # type: ignore
        raise NotImplemented(  # type: ignore
            "DataframeObjectMixin() should not be called directly. Use `@dataframeobject` annotation"
        )

    async def _serialize(self) -> Optional[DataObject]:
        datasets = {}
        for field in fields(self):  # type: ignore
            if _is_dataframe_field(field):
                dataframe = getattr(self, field.name)
                dataset = (
                    None if dataframe is None else await self.__storage.save(dataframe)
                )
                datasets[field.name] = dataset
            else:
                datasets[field.name] = getattr(self, field.name)
        return self.__dataframeobject__.serialized_type(**datasets)

    @classmethod
    async def _deserialize(cls, serialized: DataObject) -> "DataframeObjectMixin[DataFrameObjectType]":
        dataframes = {}
        for field in fields(cls):  # type: ignore
            if _is_dataframe_field(field):
                dataset = getattr(serialized, field.name)
                dataframe = (
                    None if dataset is None else await cls.__storage.load(dataset)
                )
                dataframes[field.name] = dataframe
            else:
                dataframes[field.name] = getattr(serialized, field.name)
        return cls(**dataframes)

    @classmethod
    def json_schema(cls, *args, **kwargs) -> Dict[str, Any]:
        schema = cls.__dataframeobject__.serialized_type.json_schema(*args, **kwargs)
        schema[cls.__name__] = schema[cls.__dataframeobject__.serialized_type.__name__]
        return schema

    def to_json(self, *args, **kwargs) -> Dict[str, Any]:
        raise RuntimeError(
            f"`{type(self).__name__}` `@dataframeobject` cannot be converted to json directly. "
            "i.e. use `return await DataFrames.serialize(obj)` to return it as a reponse."
        )


def _is_dataframe_field(field: Field) -> bool:
    return any(
        hasattr(field_type, "__dataframe__")
        for field_type in [field.type, *get_args(field.type)]
    )


def _serialized_field_type(field: Field) -> Type[Any]:
    if hasattr(field.type, "__dataframe__"):
        return Dataset
    if get_origin(field.type) is Union:
        args = get_args(field.type)
        if (
            len(args) == 2
            and any(hasattr(field_type, "__dataframe__") for field_type in args)
            and any(field_type is NoneType for field_type in args)
        ):
            return Optional[Dataset]  # type: ignore
    if _is_dataframe_field(field):
        raise TypeError(
            f"field {field.name}: only `DataframeType` or `Optional[DataFrameType]` are supported"
        )
    return field.type


def dataframeobject(
    decorated_class=None,
) -> Callable[[Type], Type[DataframeObjectMixin]]:
    """
    Decorator for dataclasses intended to be used as dataframes.
    """

    def add_dataframe_mixin(cls) -> Type[DataframeObjectMixin]:
        if hasattr(cls, "__annotations__") and hasattr(cls, "__dataclass_fields__"):
            amended_class = type(
                cls.__name__,
                (DataframeObjectMixin,) + cls.__mro__,
                dict(cls.__dict__),
                # cls.__name__, cls.__mro__, dict(cls.__dict__)
            )
            return amended_class
        return cls

    def add_dataframeobject_metadata(cls):
        serialized_fiels = [
            (field.name, _serialized_field_type(field)) for field in fields(cls)
        ]
        serialized_type = make_dataclass(cls.__name__ + "_", serialized_fiels)
        serialized_type = dataobject(serialized_type, unsafe=True)

        setattr(
            cls,
            "__dataframeobject__",
            DataframeObjectMetadata(
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

    def wrap(cls) -> Type[DataframeObjectMixin]:
        if hasattr(cls, "__dataframeobject__"):
            return cls
        amended_class = add_dataframe_mixin(cls)
        add_dataframeobject_metadata(amended_class)
        add_dataobject_annotations(
            amended_class, unsafe=False, validate=True, schema=True
        )
        return amended_class

    if decorated_class is None:
        return wrap
    return wrap(decorated_class)  # type: ignore
