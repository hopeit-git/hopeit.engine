"""
Config module: apps config data model and json loader
"""

from copy import deepcopy
from enum import Enum
from typing import Any, Dict, Optional, Type, Union, List, Generic

from hopeit.dataobjects import EventPayloadType, dataclass, dataobject, field
from hopeit.dataobjects.payload import Payload
from hopeit.server.config import (
    replace_config_args,
    replace_env_vars,
    ServerConfig,
    AuthType,
)
from hopeit.server.names import auto_path

__all__ = [
    "AppDescriptor",
    "AppSettings",
    "Env",
    "EventType",
    "EventPlugMode",
    "EventDescriptor",
    "EventSettings",
    "ReadStreamDescriptor",
    "WriteStreamDescriptor",
    "EventLoggingConfig",
    "EventStreamConfig",
    "Compression",
    "Serialization",
    "AppEngineConfig",
    "AppConfig",
    "parse_app_config_json",
]


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
            raise ValueError("name", self)
        if len(self.version) == 0:
            raise ValueError("version", self)

    def app_key(self):
        return auto_path(self.name, self.version)


Env = Dict[str, Dict[str, Union[str, float, int, bool]]]
AppSettings = Dict[str, Dict[str, Any]]


class EventType(str, Enum):
    """
    Supported event types

    GET: event triggered from api get endpoint
    POST: event triggered from api post endpoint
    STREAM: event triggered read events from stream. Can be started and stopped.
    SERVICE: event executed on demand or continuously. Long lived. Can be started and stopped.
    MULTIPART: event triggered from api postform-multipart request via endpoint.
    SETUP: event that is executed once when service is starting
    """

    GET = "GET"
    POST = "POST"
    STREAM = "STREAM"
    SERVICE = "SERVICE"
    MULTIPART = "MULTIPART"
    SETUP = "SETUP"


class StreamQueue:
    AUTO = "AUTO"

    @classmethod
    def default_queues(cls):
        return [cls.AUTO]


@dataobject
@dataclass
class ReadStreamDescriptor:
    """
    Configuration to read streams

    :field stream_name: str, base stream name to read
    :consumer_group: str, consumer group to send to stream processing engine to keep track of
        next messag to consume
    :queues: List[str], list of queue names to poll from. Each queue act as separate stream
        with queue name used as stream name suffix, where `AUTO` queue name means to consume
        events when no queue where specified at publish time, allowing to consume message with different
        priorities without waiting for all events in the stream to be consumed.
        Queues specified in this entry will be consumed by this event
        on each poll cycle, on the order specified. If not present
        only AUTO queue will be consumed. Take into account that in applications using multiple
        queue names, in order to ensure all messages are consumed, all queue names should be listed
        here including AUTO, except that the app is intentionally designed for certain events to
        consume only from specific queues. This configuration is manual to allow consuming messages
        produced by external apps.
    """

    name: str
    consumer_group: str
    queues: List[str] = field(default_factory=StreamQueue.default_queues)


class StreamQueueStrategy(str, Enum):
    """
    Different strategies to be used when reading streams from a queue and writing to another stream.

    :field PROPAGATE: original queue name will be preserved, so messages consumed from a queue will
        maintain that queue name when published
    :field DROP: queue name will be dropped, so messages will be published only to queue specified in
        `write_stream` configuration, or default queue if not specified.
    """

    PROPAGATE = "PROPAGATE"
    DROP = "DROP"


@dataobject
@dataclass
class WriteStreamDescriptor:
    """
    Configuration to publish messages to a stream

    :field: name, str: stream name
    :field: queue, List[str], queue names to be used to publish to stream.
        Each queue act as separate stream with queue name used as stream name suffix,
        allowing to publish messages to i.e. a queue that will be consumed with priority,
        or to multiple queues that will be consumed by different readers.
        Queue suffix will be propagated through events, allowing an event in a defined queue
        and successive events in following steps to be consumed using same queue name.
        Notice that queue will be applied only to messages coming from default queue
        (where queue is not specified at intial message creation). Messages consumed
        from other queues will be published using same queue name as they have when consumed.
    :field queue_stategory: strategy to be used when consuming messages from a stream
        with a queue name and publishing to another stream. Default is `StreamQueueStrategy.DROP`,
        so in case of complex stream propagating queue names are configured,
        `StreamQueueStrategy.PROPAGATE` must be explicitly specified.
    """

    name: str
    queues: List[str] = field(default_factory=StreamQueue.default_queues)
    queue_strategy: StreamQueueStrategy = StreamQueueStrategy.DROP


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
            self.stream_fields = ["name", "msg_id", "consumer_group"]
        self.stream_fields = [
            k if k.startswith("stream.") else f"stream.{k}" for k in self.stream_fields
        ]


class Compression(str, Enum):
    """
    Available compression algorithms and levels for event payloads.
    """

    NONE = "none"
    LZ4 = "lz4"
    LZ4_MIN = "lz4:0"
    LZ4_MAX = "lz4:16"
    ZIP = "zip"
    ZIP_MIN = "zip:1"
    ZIP_MAX = "zip:9"
    GZIP = "gzip"
    GZIP_MIN = "gzip:1"
    GZIP_MAX = "gzip:9"
    BZ2 = "bz2"
    BZ2_MIN = "bz2:1"
    BZ2_MAX = "bz2:9"
    LZMA = "lzma"


class Serialization(str, Enum):
    """
    Available serialization methods for event payloads.
    """

    JSON_UTF8 = "json"
    JSON_BASE64 = "json+base64"
    PICKLE3 = "pickle:3"
    PICKLE4 = "pickle:4"
    PICKLE5 = "pickle:5"


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
class EventSettings(Generic[EventPayloadType]):
    """
    Event execution configuration, used to parse `settings` entries in app config file where the key
    is the event name.

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
    extras: Dict[str, Any] = field(default_factory=dict)

    def __call__(self, *, key: str = "_", datatype: Type[EventPayloadType]) -> EventPayloadType:
        return Payload.from_obj(self.extras.get(key, {}), datatype=datatype)


class EventPlugMode(str, Enum):
    """
    Defines how an event route is plugged into apps when
    it is used as a plugin.

    STANDALONE: The event is added as a normal route where it is defined. Not added to apps.
    ON_APP: The event route is added only to app routes where it is used as a plugin.
    """

    STANDALONE = "Standalone"
    ON_APP = "OnApp"


class EventConnectionType(str, Enum):
    """
    Event connection type
    """

    GET = "GET"
    POST = "POST"


@dataobject
@dataclass
class EventConnection:
    """
    EventConnection: describes dependencies on this event when calling
    event on apps configured in `app_connections` sections. Only events
    specified are allowed to be invoked using `hopeit.client`

    :field: app_connection, str: key of app entry used in app_connections sections
    :field: event, str: target event_name to be called
    :filed: type, EventConnectionType: a valid event connection type, i.e. GET or POST
    :field: route, optional str: custom route in case event is not attached to default `app/version/event`
    """

    app_connection: str
    event: str
    type: EventConnectionType


@dataobject
@dataclass
class EventDescriptor:
    """
    Event Descriptor: configures event implementation

    :field: type, EventType: type of event i.e.: GET, POST, MULTIPART, STREAM, SERVICE, SETUP
    :field: plug_mode, EventPlugMode: defines whether an event defined in a plugin is created in the
        current app (ON_APP) or it will be created in the original plugin (STANDALONE, default)
    :field: route, optional str: custom route for endpoint. If not specified route will be derived
        from `/api/app_name/app_version/event_name`
    :field: impl, optional str: custom event implementation Python module. If not specified, module
        with same same as event will be imported.
    :field: connections, list of EventConnection: specifies dependencies on other apps/endpoints,
        that can be used by client plugins to call events on external apps
    :field: read_stream, optional ReadStreamDescriptor: specifies source stream to read from.
        Valid only for STREAM events.
    :field: write_stream, optional WriteStreamDescriptor: for any type of events, resultant dataobjects will
        be published to the specified stream.
    :field: auth, list of AuthType: supported authentication schemas for this event. If not specified
        application default will be used.
    :field: setting_keys, list of str: by default EventContext will have access to the settings section
        with the same name of the event using `settings = context.settings(datatype=MySettingsType)`.
        In case additional sections are needed to be accessed from
        EventContext, then a list of setting keys, including the name of the event if needed,
        can be specified here. Then access to a `custom` key can be done using
        `custom_settings = context.settings(key="customer", datatype=MyCustomSettingsType)`
    :field: dataobjects, list of str: list of full qualified dataobject types that this event can process.
        When not specified, the engine will inspect the module implementation and find all datatypes supported
        as payload in the functions defined as `__steps__`. In case of generic functions that support
        `payload: DataObject` argument, then a list of full qualified datatypes must be specified here.
    :field: group, str: group name, if none is assigned it is automatically assigned as 'DEFAULT'.
    """

    DEFAULT_GROUP = "DEFAULT"

    type: EventType
    plug_mode: EventPlugMode = EventPlugMode.STANDALONE
    route: Optional[str] = None
    impl: Optional[str] = None
    connections: List[EventConnection] = field(default_factory=list)
    read_stream: Optional[ReadStreamDescriptor] = None
    write_stream: Optional[WriteStreamDescriptor] = None
    auth: List[AuthType] = field(default_factory=list)
    setting_keys: List[str] = field(default_factory=list)
    dataobjects: List[str] = field(default_factory=list)
    group: str = DEFAULT_GROUP

    def __post_init__(self):
        if self.read_stream:
            assert (
                "{auto}" not in self.read_stream.name
            ), "read_stream.name should be defined. {auto} is not allowed."


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
    :cors_routes_prefix: routes prefix to apply CORS origin to. If not specified `/api/app-name/version/` will be used
    """

    import_modules: Optional[List[str]] = None
    read_stream_timeout: int = 1000
    read_stream_interval: int = 1000
    default_stream_compression: Compression = Compression.LZ4
    default_stream_serialization: Serialization = Serialization.JSON_BASE64
    track_headers: List[str] = field(default_factory=list)
    cors_origin: Optional[str] = None
    cors_routes_prefix: Optional[str] = None

    def __post_init__(self):
        self.track_headers = [
            k if k.startswith("track.") else f"track.{k}" for k in self.track_headers
        ]
        if "track.request_ts" not in self.track_headers:
            self.track_headers = ["track.request_ts"] + self.track_headers
        if "track.request_id" not in self.track_headers:
            self.track_headers = ["track.request_id"] + self.track_headers


@dataobject
@dataclass
class AppConnection:
    """
    AppConnections: metadata to initialize app client in order to connect
    and issue requests to other running apps

    :field: name, str: target app name to connect to
    :field: version, str: target app version
    :field: client, str: hopeit.app.client.Client class implementation, from available client plugins
    :field: settings, optional str: key under `settings` section of app config containing connection configuration,
        if not specified, plugin will lookup its default section usually the plugin name. But in case multiple
        clients need to be configured, this value can be overridden.
    """

    name: str
    version: str
    client: str = "<<NO CLIENT CONFIGURED>>"
    settings: Optional[str] = None
    plugin_name: Optional[str] = None
    plugin_version: Optional[str] = None


@dataobject
@dataclass
class AppConfig:
    """
    App Configuration container
    """

    app: AppDescriptor
    engine: AppEngineConfig = field(default_factory=AppEngineConfig)
    app_connections: Dict[str, AppConnection] = field(default_factory=dict)
    env: Env = field(default_factory=dict)
    events: Dict[str, EventDescriptor] = field(default_factory=dict)
    server: Optional[ServerConfig] = None
    plugins: List[AppDescriptor] = field(default_factory=list)
    settings: AppSettings = field(default_factory=dict)
    effective_settings: Optional[AppSettings] = None

    def app_key(self):
        return self.app.app_key()

    def setup(self):
        self.effective_settings = {}
        self._setup_streams_settings()
        self._setup_event_extra_settings()
        return self

    def _setup_streams_settings(self):
        """
        Prepares missing or default values for events stream configuration:

        1) Completes missing event streams settings using settings key
            from write_stream or read_stream name
        2) Sets default compression and serialization for streams based on server config
        """
        for event_name, event_info in self.events.items():
            stream_settings = {}
            if event_info.write_stream:
                stream_settings.update(self.settings.get(event_info.write_stream.name, {}))
            elif event_info.read_stream:
                stream_settings.update(self.settings.get(event_info.read_stream.name, {}))
            settings_data = deepcopy(self.settings.get(event_name, {"stream": {}}))
            stream_settings.update(settings_data.get("stream", {}))
            settings_data["stream"] = stream_settings
            settings: EventSettings = Payload.from_obj(settings_data, datatype=EventSettings)
            if settings.stream.compression is None:
                settings.stream.compression = self.engine.default_stream_compression
            if settings.stream.serialization is None:
                settings.stream.serialization = self.engine.default_stream_serialization
            self.effective_settings[event_name] = Payload.to_obj(settings)

    def _setup_event_extra_settings(self):
        """
        Add to event settings section extra keys references in `setting_keys` property
        of EventDescriptor, so these are available in `EventContext` using
        `context.settings(key, datatype)

        For these extra keys, validation is not perform until accessed.
        """
        for event_name, event_info in self.events.items():
            extras = {}
            if event_name in self.settings:
                extras["_"] = self.settings[event_name]
            for key in event_info.setting_keys:
                value = self.settings.get(key)
                if value is not None:
                    extras[key] = value
            self.effective_settings[event_name]["extras"] = extras


def parse_app_config_json(config_json: str) -> AppConfig:
    """
    Parses configuration json file contents into AppConfig data structure.
    Before conversion, parameters enclosed with { } are replaced by its
    respective values (@see _replace_args)
    """
    effective_config_json = replace_env_vars(config_json)
    app_config: AppConfig = Payload.from_json(effective_config_json, datatype=AppConfig)
    replace_config_args(
        parsed_config=app_config,
        config_classes=(
            AppDescriptor,
            EventDescriptor,
            ReadStreamDescriptor,
            WriteStreamDescriptor,
            AppConnection,
            EventConnection,
            EventSettings,
        ),
        auto_prefix=app_config.app.app_key(),
    )
    return app_config.setup()
