"""
Data Objects type abstractions.
A Dataobject is basically any object like a regular dataclass but adapted to implement
pydantic.BaseModel functionallity plus specific hopeit.engine functionallity to make it
able to be stored, retrieved, serialized and deserialized by the platform toolkit.

Annotate classes with `@dataobject` annotation to make it support:
    - JSON schema generation, validation and serialization/deserialization
    - Compression and Serialization using different mechanisms

Example:

    from hopeit.dataobjects import dataobject

    @dataobject
    class MyObject:
        name: str
        number: int
"""
import uuid
from datetime import datetime
from typing import TypeVar, Optional, Union, ClassVar

from pydantic import BaseModel, Field, ValidationError

__all__ = ['EventPayload',
           'EventPayloadType',
           'StreamEventParams',
           'dataobject',
           'Field',
           'ValidationError',
           'DataObject',
           'payload']


class StreamEventParams(BaseModel):
    """
    Helper class used to access attributes in @dataobject
    decorated objects, based on dot notation expressions
    """
    event_id_expr: Optional[str]
    event_ts_expr: Optional[str]

    @staticmethod
    def extract_attr(obj, expr):
        value = obj
        for attr_name in expr.split('.'):
            if value:
                value = getattr(value, attr_name)
        return value


class StreamEventMixin:
    """
    MixIn class to add functionality for DataObjects to provide event id and event timestamp
    to be suitable for stream publishing.

    Do not use this class directly, instead use `@dataobject` class decorator.
    """

    def __init__(self, *, event_id_expr=None, event_ts_expr=None):
        self.__stream_event__ = StreamEventParams(  # pragma: no cover
            event_id_expr=event_id_expr,
            event_ts_expr=event_ts_expr
        )
        raise NotImplementedError  # must use @dataobject decorator  # pragma: no cover

    def event_id(self) -> str:
        if self.__stream_event__.event_id_expr:
            return self.__stream_event__.extract_attr(self, self.__stream_event__.event_id_expr)
        return str(uuid.uuid4())

    def event_ts(self) -> Optional[datetime]:
        if self.__stream_event__.event_ts_expr:
            return self.__stream_event__.extract_attr(self, self.__stream_event__.event_ts_expr)
        return None


DataObject = TypeVar("DataObject", bound=BaseModel)
EventPayload = Union[str, int, float, bool, dict, set, list, DataObject]
EventPayloadType = TypeVar("EventPayloadType")  # pylint: disable=invalid-name


class BinaryAttachment:
    """Type descriptor for multipart binary attachments"""


class BinaryDownload(BaseModel):
    """
    Type descriptor for binary download. Events returning files to download
    should specialize this class for specififc content types, i.e.:

    ```
    @dataobject
    class ImagePng(BinaryDownload):
        content_type = "image/png"
    ```

    This way, the  type can be used in event API specification as response type.
    """
    content_type: ClassVar[str] = "application/octet-stream"


_EXCLUDE_CLASS_MEMBERS = {
    "__dict__", "__weakref__"
}


def dataobject(
        decorated_class=None, *,
        event_id: Optional[str] = None,
        event_ts: Optional[str] = None,
        schema: bool = True):
    """
    Decorator for classes intended to be used in API and/or streams. This decorated mainly implements
    pydantic.BaseModel adding dataclass functionality to:
        * Generate Json Schema for Open API definition
        * Parse and convert from and to json
        * Validate Json against Json schema
        * Detect incompatibilities between API specification and payload structures
        * Detect undocumented API changes early (i.e. fields added or changed)

    In general, all dataobjects that are to be exchanged using API endpoints (payload and responses),
    or write and read from streams, need to implement @dataobject decorator.

    In order to publish instances to streams, an event id and event timestamp
    can be extracted. StreamManager does that automatically for classes defining
    event_id() and event_ts() methods.

    This decorator, adds these two methods to a class:
    `event_id()`: str, extract the id of the object from a given dot notation expression
    `event_ts()`: Optional[datetime], extract timestamp from a given dot notation expression

    :param decorated_class: decorated class
    :param event_id: optional str, dot notation expression
        to navigate to id field (i.e. 'id' or 'event.id')
    :param event_ts: optional str, dot notation expression
        to navigate to a datetime field (i.e. 'last_update.ts')
    :param schema: bool, default True: indicates to attempt json_schema generation in API module

    In case event_id is not provided, an uuid will be generated on each call to `event_id()`
    In case event_ts is not provided, None will be returned on each call to `event_ts()`

    Example::

        @dataobject
        class StatusChange:
            ts: datetime
            status: str

        @dataobject(event_id='id', event_ts='last_status.ts', unsafe=True, validate=False)
        class EventData:
            id: str
            last_status: StatusChange

    """

    def wrap(cls):
        amended_class = type(
            cls.__name__,
            (*({cls.__mro__[1]} - {object}), BaseModel),
            {
                k: v for k, v in cls.__dict__.items()
                if k not in _EXCLUDE_CLASS_MEMBERS
            }
        )
        setattr(amended_class, '__data_object__', {'schema': schema})
        setattr(amended_class, '__stream_event__', StreamEventParams(
            event_id_expr=event_id,
            event_ts_expr=event_ts
        ))
        setattr(amended_class, 'event_id', StreamEventMixin.event_id)
        setattr(amended_class, 'event_ts', StreamEventMixin.event_ts)
        return amended_class

    if decorated_class is None:
        return wrap
    return wrap(decorated_class)
