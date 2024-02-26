"""
`@dataframeobject` annonation mixin to serialize a group of `@dataframe`s.

Datasets behaves as DataObject so they can be used as payload
for endpoints and streams.
"""

from dataclasses import dataclass, fields, make_dataclass
from typing import Any, Callable, Dict, Generic, Type, TypeVar

from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataobjects import (
    DataObject,
    StreamEventMixin,
    StreamEventParams,
    dataobject,
)

DataFrameType = TypeVar("DataFrameType")


@dataclass
class DataframeObjectMetadata:
    dataframe_types: Dict[str, DataFrameType]
    serialized_type: Type[DataObject]


class DataframeObjectMixin(Generic[DataFrameType]):
    """
    MixIn class to add functionality for `@dataframeobject`s

    Do not use this class directly, instead use `@dataframeobject` class decorator.
    """

    def __init__(self) -> None:
        raise NotImplemented(
            "DataframeObjectMixin() should not be called directly. Use `@dataframeobject` annotation"
        )

    async def serialize(self):
        datasets = {}
        for field in fields(self):
            if hasattr(field.type, "__dataframe__"):
                dataframe = getattr(self, field.name)
                dataset = await self.__storage.save(dataframe)
                datasets[field.name] = dataset
            else:
                datasets[field.name] = getattr(self, field.name)
        return self.__dataframeobject__.serialized_type(**datasets)

    @classmethod
    async def deserialize(cls, serialized: DataObject):
        dataframes = {}
        for field in fields(cls):
            if hasattr(field.type, "__dataframe__"):
                dataset = getattr(serialized, field.name)
                dataframe = await cls.__storage.load(dataset)
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
             "i.e. use `return await payload.serialize()` to return it as a reponse."
        )


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
            (field.name, Dataset if hasattr(field.type, "__dataframe__") else field.type)
            for field in fields(cls)
        ]
        serialized_type = make_dataclass(cls.__name__ + "_", serialized_fiels)
        serialized_type = dataobject(serialized_type)

        setattr(
            cls,
            "__dataframeobject__",
            DataframeObjectMetadata(
                dataframe_types={},
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
