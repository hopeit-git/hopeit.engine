"""
`@dataframeobject` annonation mixin to serialize a group of `@dataframe`s.

Datasets behaves as DataObject so they can be used as payload
for endpoints and streams.
"""

import dataclasses
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

from pydantic import TypeAdapter, create_model
from pydantic.fields import FieldInfo

from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import (
    DataObject,
    StreamEventMixin,
    StreamEventParams,
    dataobject,
    fields,
)

DataFrameObjectT = TypeVar("DataFrameObjectT")
NoneType = type(None)


@dataclasses.dataclass
class DataFrameObjectMetadata(Generic[DataObject]):
    serialized_type: Type[DataObject]


class DataFrameObjectMixin(Generic[DataFrameObjectT]):
    """
    MixIn class to add functionality for `@dataframeobject`s

    Do not use this class directly, instead use `@dataframeobject` class decorator.
    """

    __storage: ClassVar[Any] = None  # pylint: disable=invalid-name

    def __init__(self) -> None:
        self.__dataframeobject__: DataFrameObjectMetadata = None  # type: ignore
        raise NotImplementedError(
            "DataFrameObjectMixin() should not be called directly. Use `@dataframeobject` annotation"
        )

    async def _serialize(self) -> Optional[DataObject]:
        """Saves internal `@dataframe`s using configured serialization protocol
        and returns json-serialiable dataobject
        """
        datasets = {}
        for field_name, field in fields(self).items():  # type: ignore[arg-type]
            if Dataset in {field.annotation, *get_args(field.annotation)}:
                dataframe = getattr(self, field_name)
                dataset = (
                    None if dataframe is None else await self.__storage.save(dataframe)
                )
                datasets[field_name] = dataset
            else:
                datasets[field_name] = getattr(self, field_name)
        return self.__dataframeobject__.serialized_type(**datasets)

    @classmethod
    async def _deserialize(
        cls, serialized: DataObject
    ) -> "DataFrameObjectMixin[DataFrameObjectT]":
        """From a serialized datframeobject, load inner `@dataframe` objects
        and returns a `@dataframeobject` instance"""
        dataframes = {}
        for field_name, field in fields(cls).items():  # type: ignore[type-var]
            if Dataset in {field.annotation, *get_args(field.annotation)}:
                dataset = getattr(serialized, field_name)
                dataframe = (
                    None if dataset is None else await cls.__storage.load(dataset)
                )
                dataframes[field_name] = dataframe
            else:
                dataframes[field_name] = getattr(serialized, field_name)
        return cls(**dataframes)

    @classmethod
    def json_schema(cls, *args, **kwargs) -> Dict[str, Any]:
        schema = TypeAdapter(cls.__dataframeobject__.serialized_type).json_schema(*args, **kwargs)
        return schema

    # def to_json(self, *args, **kwargs) -> Dict[str, Any]:
    #     raise RuntimeError(
    #         f"`{type(self).__name__}` `@dataframeobject` cannot be converted to json directly. "
    #         "i.e. use `return await DataFrames.serialize(obj)` to return it as a response."
    #     )


def _is_dataframe_field(field: FieldInfo) -> bool:
    return any(
        hasattr(field_type, "__dataframe__")
        for field_type in [field.annotation, *get_args(field.annotation)]
    )


def _serialized_field_type(field_name: str, field: FieldInfo) -> Optional[Type[Any]]:
    """Computes the `@dataobject` datatype used as a result
    of serialized `@dataframeobject`
    """
    if hasattr(field.annotation, "__dataframe__"):
        return Dataset
    if get_origin(field.annotation) is Union:
        args = get_args(field.annotation)
        if (
            len(args) == 2
            and any(hasattr(field_type, "__dataframe__") for field_type in args)
            and any(field_type is NoneType for field_type in args)
        ):
            return Optional[Dataset]  # type: ignore
    if _is_dataframe_field(field):
        raise TypeError(
            f"field {field_name}: only `DataFrameT` or `Optional[DataFrameT]` are supported"
        )
    return field.annotation


def dataframeobject(
    decorated_class=None,
) -> Callable[[Type], Type[DataFrameObjectMixin]]:
    """
    Decorator for dataclasses intended to be used as dataframes.
    """

    def add_dataframe_mixin(cls) -> Type[DataFrameObjectMixin]:
        if hasattr(cls, "__annotations__") and hasattr(cls, "__dataclass_fields__"):
            amended_class = type(
                cls.__name__,
                (DataFrameObjectMixin,) + cls.__mro__,
                dict(cls.__dict__),
            )
            return amended_class
        return cls

    def add_dataframeobject_metadata(cls):
        serialized_fields = {
            field_name: (_serialized_field_type(field_name, field_info), field_info)
            for field_name, field_info in fields(cls).items()
        }
        serialized_type = create_model(cls.__name__+"_", **serialized_fields)
        serialized_type = dataobject(serialized_type, unsafe=True)
        setattr(
            cls,
            "__dataframeobject__",
            DataFrameObjectMetadata(
                serialized_type=serialized_type,
            ),
        )

    def add_dataobject_annotations(cls, unsafe: bool, schema: bool):
        setattr(
            cls,
            "__data_object__",
            {"unsafe": unsafe, "schema": schema},
        )
        setattr(cls, "__stream_event__", StreamEventParams(None, None))
        setattr(cls, "event_id", StreamEventMixin.event_id)
        setattr(cls, "event_ts", StreamEventMixin.event_ts)

    def wrap(cls) -> Type[DataFrameObjectMixin]:
        if hasattr(cls, "__dataframeobject__"):
            return cls
        add_dataframeobject_metadata(cls)
        amended_class = add_dataframe_mixin(cls)
        add_dataobject_annotations(
            amended_class, unsafe=False, schema=True
        )
        return amended_class

    if decorated_class is None:
        return wrap
    return wrap(decorated_class)  # type: ignore
