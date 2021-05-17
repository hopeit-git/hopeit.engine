"""
Data Objects type abstractions.
A Dataobject is basically any object wrapped in a Dataclass and that is able
to be stored, retrieved, serialized and deserialized by the platform toolkit.

Annotate dataclasses with @dataobject annotation to make it support:
    - JSON schema generation, validation and serialization/deserialization
    - Compression and Serialization using different mechanisms

Example:

    from hopeit.dataobjects import dataclass, dataobject

    @dataobject
    @dataclass
    class MyObject:
        name: str
        number: int
"""
import pickle
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TypeVar, Optional, Union, Any

from dataclasses_jsonschema import JsonSchemaMixin

__all__ = ['EventPayload',
           'EventPayloadType',
           'StreamEventParams',
           'dataobject',
           'DataObject',
           'copy_payload',
           'jsonify']


@dataclass
class StreamEventParams:
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

    Do not use this class directly, instead use `@databoject` class decorator.
    """

    def __init__(self, *, event_id_expr=None, event_ts_expr=None):
        self.__stream_event__ = StreamEventParams(event_id_expr, event_ts_expr)  # pragma: no cover
        raise NotImplementedError  # must use @dataobject decorator  # pragma: no cover

    def event_id(self) -> str:
        if self.__stream_event__.event_id_expr:
            return self.__stream_event__.extract_attr(self, self.__stream_event__.event_id_expr)
        return str(uuid.uuid4())

    def event_ts(self) -> Optional[datetime]:
        if self.__stream_event__.event_ts_expr:
            return self.__stream_event__.extract_attr(self, self.__stream_event__.event_ts_expr)
        return None


DataObject = TypeVar("DataObject", bound=JsonSchemaMixin)
EventPayload = Union[str, int, float, bool, dict, set, list, DataObject]
EventPayloadType = TypeVar("EventPayloadType")


class BinaryAttachment:
    """Type descriptor for multipart binary attachments"""


class BinaryDownload:
    """
    Type descriptor for binary download. Events returning files to download
    should specialize this class for specififc content types, i.e.:

    ```
    @dataobject
    @dataclass
    class ImagePng(BinaryDownload):
        content_type = "image/png"
    ```

    This way, the  type can be used in event API speficacation as reponse type.
    """
    content_type: str = "application/octet-stream"


def dataobject(
        decorated_class=None, *,
        event_id: Optional[str] = None,
        event_ts: Optional[str] = None,
        unsafe: bool = False,
        validate: bool = True,
        schema: bool = True):
    """
    Decorator for dataclasses intended to be used in API and/or streams. This decorated mainly implements
    JsonSchemaMixIn adding dataclass functionality to:
        * Generate Json Schema for Open API definition
        * Parse and convert from and to json
        * Validate Json against Json schema
        * Detect incompatibilities between API specification and payload structures
        * Detect undocumented API changes early (i.e. fields added or changed)

    In general, all dataclasses that are to be exchanged using API endpoints (payload and responses),
    or write and read from streams, need to implement @dataobject and decorator in addition to Python
    @dataclass decorator.

    In order to publish instances to streams, an event id and event timestamp
    can be extracted. StreamManager does that automatically for classes defining
    event_id() and event_ts() methods.

    This decorator, adds these two methods to a dataclass:
    `event_id()`: str, extract the id of the object from a given dot notation expression
    `event_ts()`: Optional[datetime], extract timestamp from a given dot notation expression

    :param decorated_class: decorated class
    :param event_id: optional str, dot notation expression
        to navigate to id field (i.e. 'id' or 'event.id')
    :param event_ts: optional str, dot notation expression
        to navigate to a datetime field (i.e. 'last_update.ts')
    :param unsafe: bool, default False. When False, every time a new step is invoked a copy of
        dataobject will be sent, preventing object to be mutated unintentionally.
        Specifying unsafe=True prevents making copies every time a step is invoked, improving performance.
        Use with caution: with unsafe=True, you can accidentally mutate objects after they are yield,
        specially when returning generators or `Spawn[...]`.
    :param validate: bool, default True: indicates whether to validate using JsonSchema automatically generated
        by `@dataobject` annotation when reading from and converting to json using `Json.from_json` and
        `Json.to_json`. Notice that if you call from_json or to_json directly from annotated dataobject
        you need to specify validate=True/False parameter value.
    :param schema: bool, default True: indicates to attempt json_schema generation in API module

    In case event_id is not provided, an uuid will be generated on each call to `event_id()`
    In case event_ts is not provided, None will be returned on each call to `event_ts()`

    Example::

        @dataobject
        @dataclass
        class StatusChange:
            ts: datetime
            status: str

        @dataobject(event_id='id', event_ts='last_status.ts', unsafe=True, validate=False)
        @dataclass
        class EventData:
            id: str
            last_status: StatusChange

    """

    def wrap(cls):
        amended_class = _add_jsonschema_support(cls)
        setattr(amended_class, '__data_object__', {'unsafe': unsafe, 'validate': validate, 'schema': schema})
        setattr(amended_class, '__stream_event__', StreamEventParams(event_id, event_ts))
        setattr(amended_class, 'event_id', StreamEventMixin.event_id)
        setattr(amended_class, 'event_ts', StreamEventMixin.event_ts)
        return amended_class

    if decorated_class is None:
        return wrap
    return wrap(decorated_class)


def _add_jsonschema_support(cls):
    if hasattr(cls, '__data_object__'):
        return cls
    if hasattr(cls, '__annotations__') and hasattr(cls, '__dataclass_fields__'):
        amended_class = type(cls.__name__,
                             (JsonSchemaMixin,) + cls.__mro__,
                             dict(cls.__dict__))
        return amended_class
    return cls


def _binary_copy(payload: Any) -> Any:
    return pickle.loads(pickle.dumps(payload, protocol=4))


def copy_payload(original: Optional[EventPayload]) -> Optional[EventPayload]:
    """
    Creates a copy of the original DataObject in case it is mutable.
    Returns original object in case it is a frozen dataclass
    """
    if original is None:
        return None
    if isinstance(original, (str, int, float, bool, tuple, Decimal)):  # immutable supported types
        return original
    if isinstance(original, (dict, set, list)):
        return _binary_copy(original)
    if hasattr(original, '__dataclass_params__') and original.__dataclass_params__.frozen:  # type: ignore
        return original
    if hasattr(original, '__data_object__') and original.__data_object__['unsafe']:
        return original
    return _binary_copy(original)
