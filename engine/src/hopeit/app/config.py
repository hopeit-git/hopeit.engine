"""
Config module: apps config data model and json loader
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Union, List

from hopeit.dataobjects import dataobject
from hopeit.server.config import replace_config_args, replace_env_vars, ServerConfig, AuthType
from hopeit.server.names import auto_path

__all__ = ['AppDescriptor',
           'Env',
           'EventType',
           'EventPlugMode',
           'EventDescriptor',
           'EventConfig',
           'StreamDescriptor',
           'EventLoggingConfig',
           'EventStreamConfig',
           'Compression',
           'Serialization',
           'AppEngineConfig',
           'AppConfig',
           'parse_app_config_json']


@dataobject
@dataclass
class AppDescriptor:
    """
    App descriptor
    """
    name: str
    version: str

    def __post_init__(self):
        if len(self.name) == 0:
            raise ValueError('name', self)
        if len(self.version) == 0:
            raise ValueError('version', self)

    def app_key(self):
        return auto_path(self.name, self.version)


Env = Dict[str, Dict[str, Union[str, float, bool]]]


class EventType(Enum):
    """
    Supported event types

    GET: event triggered from api get endpoint
    POST: event triggered from api post endpoint
    STREAM: event triggered read events from stream. Can be started and stopped.
    SERVICE: event executed on demand or continuously. Long lived. Can be started and stopped.
    MULTIPART: event triggered from api postform-multipart request via endpoint.
    """
    GET = 'GET'
    POST = 'POST'
    STREAM = 'STREAM'
    SERVICE = 'SERVICE'
    MULTIPART = 'MULTIPART'


@dataobject
@dataclass
class StreamDescriptor:
    name: str
    consumer_group: Optional[str] = None


@dataobject
@dataclass
class EventLoggingConfig:
    """
    Logging configuration specific for the event

    :field extra_fields: list of str, extra fields required to apps when logging
        as part of extra(...) call
    :field stream_fields: list of str, field names to extra when reading streams,
        valid options are
            'name': stream name,
            'msg_id', internal message id
            'consumer_group', conaumer group name
            'submit_ts', utc time message was submited to stream
            'event_ts', event timestamp from @data_event
            'event_id', event id from @data_event
            'read_ts': uct time when message was consumed from stream
    """
    extra_fields: List[str] = field(default_factory=list)
    stream_fields: List[str] = field(default_factory=list)

    def __post_init__(self):
        if len(self.stream_fields) == 0:
            self.stream_fields = ['name', 'msg_id', 'consumer_group']
        self.stream_fields = [k if k.startswith('stream.') else f"stream.{k}"
                              for k in self.stream_fields]


class Compression(Enum):
    """
    Available compression algorithms and levels for event payloads.
    """
    NONE = 'none'
    LZ4 = 'lz4'
    LZ4_MIN = 'lz4:0'
    LZ4_MAX = 'lz4:16'
    ZIP = 'zip'
    ZIP_MIN = 'zip:1'
    ZIP_MAX = 'zip:9'
    GZIP = 'gzip'
    GZIP_MIN = 'gzip:1'
    GZIP_MAX = 'gzip:9'
    BZ2 = 'bz2'
    BZ2_MIN = 'bz2:1'
    BZ2_MAX = 'bz2:9'
    LZMA = 'lzma'


class Serialization(Enum):
    """
    Available serialization methods for event payloads.
    """
    JSON_UTF8 = 'json'
    JSON_BASE64 = 'json+base64'
    PICKLE3 = 'pickle:3'
    PICKLE4 = 'pickle:4'
    PICKLE5 = 'pickle:5'


@dataobject
@dataclass
class EventStreamConfig:
    """
    Stream configuration for STREAM events
    :field timeout: float, timeout for stream processing im seconds. If timeout is exceeded event
        processing will be cancelled. Default 60 seconds
    :field target_max_len: int, default 0, max number of elements to be used as a target
        for the stream collection size. Messages above this value might be dropped
        from the collection when new items are added. Notice that the number of the items
        in the collection could exceed temporary this value to allow optimized behaviour,
        but no items will be dropped until the collection exceeds target_max_len.
        With default value of 0, collection size is unlimited and items should be removed by apps.
    :field throttle_ms: int, milliseconds specifying minimum duration for each event
    :filed step_delay: int, milliseconds to sleep between steps
    :field batch_size: int, number of max messages to process each time when reading stream,
        set to 1 to ensure min losses in case of process stop, set higher for performance
    :field compression: Compression, compression algorithm used to send messages to stream, if not specified
        default from Server config will be used.
    :field serialization: Serialization, serialization method used to send messages to stream, if not specified
        default from Server config will be used.
    """
    timeout: float = 60.0
    target_max_len: int = 0
    throttle_ms: int = 0
    step_delay: int = 0
    batch_size: int = 100
    compression: Optional[Compression] = None
    serialization: Optional[Serialization] = None


@dataobject
@dataclass
class EventConfig:
    """
    Event execution configuration
    :field response_timeout: float, default 60.0: seconds to timeout waiting for event execution
        when invoked externally .i.e. GET or POST events. If exceeded, Timed Out response will be returned.
        Notice that this timeout does not apply for stream processing events. Use EventStreamsConfig.timeout
        to set up timeout on stream processing.
    :field logging: EventLoggingConfig, configuration for logging for this particular event
    :field stream: EventStreamConfig, configuration for stream processing for this particular event
    """
    response_timeout: float = 60.0
    logging: EventLoggingConfig = field(default_factory=EventLoggingConfig)
    stream: EventStreamConfig = field(default_factory=EventStreamConfig)


class EventPlugMode(Enum):
    """
    Defines how an event route is plugged into apps when
    it is used as a plugin.

    STANDALONE: The event is added as a normal route where it is defined. Not added to apps.
    ON_APP: The event route is added only to app routes where it is used as a plugin.
    """
    STANDALONE = 'Standalone'
    ON_APP = 'OnApp'


@dataobject
@dataclass
class EventDescriptor:
    """
    Event descriptor
    """
    type: EventType
    plug_mode: EventPlugMode = EventPlugMode.STANDALONE
    route: Optional[str] = None
    read_stream: Optional[StreamDescriptor] = None
    write_stream: Optional[StreamDescriptor] = None
    config: EventConfig = field(default_factory=EventConfig)
    auth: List[AuthType] = field(default_factory=list)

    def __post_init__(self):
        if self.read_stream:
            assert '{auto}' not in self.read_stream.name, \
                "read_stream.name should be defined. {auto} is not allowed."


@dataobject
@dataclass
class AppEngineConfig:
    """
    Engine specific parameters shared among events

    :field import_modules: list of string with the python module names to import to find
        events and datatype implementations
    :field read_stream_timeout: timeout in milliseconds to block connection pool when waiting for stream events
    :field read_stream_interval: delay in milliseconds to wait before attempting a new batch. Use to prevent
        connection pool to be blocked constantly.
    :track_headers: list of required X-Track-* headers
    :cors_origin: allowed CORS origin for web server
    """
    import_modules: Optional[List[str]] = None
    read_stream_timeout: int = 1000
    read_stream_interval: int = 1000
    default_stream_compression: Compression = Compression.LZ4
    default_stream_serialization: Serialization = Serialization.JSON_BASE64
    track_headers: List[str] = field(default_factory=list)
    cors_origin: Optional[str] = None

    def __post_init__(self):
        self.track_headers = [k if k.startswith('track.') else f"track.{k}" for k in self.track_headers]
        if 'track.request_ts' not in self.track_headers:
            self.track_headers = ['track.request_ts'] + self.track_headers
        if 'track.request_id' not in self.track_headers:
            self.track_headers = ['track.request_id'] + self.track_headers


@dataobject
@dataclass
class AppConfig:
    """
    App Configuration container
    """
    app: AppDescriptor
    engine: AppEngineConfig = field(default_factory=AppEngineConfig)
    env: Env = field(default_factory=dict)
    events: Dict[str, EventDescriptor] = field(default_factory=dict)
    server: Optional[ServerConfig] = None
    plugins: List[AppDescriptor] = field(default_factory=list)

    def app_key(self):
        return self.app.app_key()

    def __post_init__(self):
        for event in self.events.values():
            if event.config.stream.compression is None:
                event.config.stream.compression = self.engine.default_stream_compression
            if event.config.stream.serialization is None:
                event.config.stream.serialization = self.engine.default_stream_serialization


def parse_app_config_json(config_json: str) -> AppConfig:
    """
    Parses configuration json file contents into AppConfig data structure.
    Before conversion, parameters enclosed with { } are replaced by its
    respective values (@see _replace_args)
    """
    # effective_config_json = _replace_args(config_json)
    effective_config_json = replace_env_vars(config_json)
    app_config = AppConfig.from_json(effective_config_json)  # type: ignore
    replace_config_args(
        parsed_config=app_config,
        config_classes=(AppDescriptor, EventDescriptor, StreamDescriptor),
        auto_prefix=app_config.app.app_key()
    )
    return app_config
