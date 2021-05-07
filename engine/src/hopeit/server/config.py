"""
Server configuration utility
"""
from enum import Enum
from typing import TypeVar, List, Optional
import re
import os

from dataclasses import dataclass, field

from hopeit.dataobjects import dataobject
from hopeit.server.names import auto_path_prefixed

__all__ = ['StreamsConfig',
           'LoggingConfig',
           'AuthType',
           'AuthConfig',
           'ServerConfig',
           'parse_server_config_json',
           'replace_env_vars',
           'replace_config_args']


DEFAULT_STR = "<<DEFAULT>>"
ConfigType = TypeVar("ConfigType")


@dataobject
@dataclass
class StreamsConfig:
    """
    :field connection_str: str, url to connect to streams server: i.e. redis://localhost:6379
    """
    stream_manager: str = "hopeit.streams.NoStreamManager"
    connection_str: str = '<<NoStreamManager>>'
    delay_auto_start_seconds: int = 3


@dataobject
@dataclass
class LoggingConfig:
    log_level: str = 'INFO'
    log_path: str = 'logs/'


class AuthType(str, Enum):
    """
    Supported Authorization/Authentication types
    """
    UNSECURED = 'Unsecured'
    BASIC = 'Basic'
    BEARER = 'Bearer'
    REFRESH = 'Refresh'


@dataobject
@dataclass
class AuthConfig:
    """
    Server configuration to handle authorization tokens
    """
    secrets_location: str
    auth_passphrase: str
    enabled: bool = True
    create_keys: bool = False
    domain: Optional[str] = None
    encryption_algorithm: str = 'RS256'
    default_auth_methods: List[AuthType] = field(default_factory=list)

    def __post_init__(self):
        if len(self.default_auth_methods) == 0:
            self.default_auth_methods.append(AuthType.UNSECURED)

    @staticmethod
    def no_auth():
        return AuthConfig('', '', enabled=False)


@dataobject
@dataclass
class APIConfig:
    docs_path: Optional[str] = None


@dataobject
@dataclass
class ServerConfig:
    streams: StreamsConfig = field(default_factory=StreamsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    auth: AuthConfig = field(default_factory=AuthConfig.no_auth)
    api: APIConfig = field(default_factory=APIConfig)


def parse_server_config_json(config_json: str) -> ServerConfig:
    """
    Parses configuration json file contents into EngineConfig data structure.
    Before conversion, parameters enclosed with { } are replaced by its
    respective values (@see _replace_args)
    """
    effective_json = replace_env_vars(config_json)
    parsed_config = ServerConfig.from_json(effective_json)  # type: ignore
    replace_config_args(
        parsed_config=parsed_config,
        config_classes=tuple([StreamsConfig])
    )
    return parsed_config


def replace_env_vars(config_json: str) -> str:
    """
    Replaces env variables matching form ${VAR_NAME} with its string value
    :param config_json: input configuratio json as string
    :return: str, with replaced values
    :raise: AssertionError if variables matching ${VAR_NAME} form are not replaced
    """
    result = config_json
    env_re = re.compile('\\${([^}{]+)}', re.IGNORECASE)
    for match in env_re.finditer(result):
        expr = match.group(0)
        var_name = match.group(1)
        value = os.getenv(var_name.upper())
        if value:
            result = result.replace(expr, value)

    missing_env_vars = env_re.findall(result)
    assert len(missing_env_vars) == 0, \
        f"Cannot get value from OS environment vars: {missing_env_vars}"

    return result


def replace_config_args(*, parsed_config: ConfigType,
                        config_classes: tuple,
                        auto_prefix: str = ''):
    """
    Replaces {...} enclosed expression in string values inside parsed_config.
    {...} expressions are paths to objects in same parsed_config object, expressed
    using dot notation. Also special name `{auto}` is replaced by the object path.
    parsed_config is modified inline and no value is returned.
    Replacement is done twice so values that refers to other generated values
    are replaced.

    Example:
    `{app.name}` will be replaced by the contents of `parsed_config.app.name`

    `{auto}` will be replaced by the path of keys to the current object
    built using dot notation and prefixed by `app.name`.`app.version`

    Example::

        AppConfig(
            app=App(name="myapp", version="1x0"),
            events={"event1": EventDescriptor(
                steps={"step1": StepDescriptor(notify="{auto}" ... )}
            )}
        )

    `{auto}` will be replaced by `myapp.1x0.event1.step1`
    """

    def _replace_in_dict(node: dict, expr: str, replacement: str):
        for k, value in node.items():
            if isinstance(value, str):
                if expr in value:
                    node[k] = value.replace(expr, replacement)
            elif isinstance(value, (dict, *config_classes)):
                _replace_in_config(value, expr, replacement)

    def _replace_in_config(node, expr: str, replacement: str):
        if isinstance(node, dict):
            _replace_in_dict(node, expr, replacement)
        else:
            for attr_name in dir(node):
                if attr_name[0] != '_' and hasattr(node, attr_name):
                    value = getattr(node, attr_name)
                    if isinstance(value, str):
                        if expr in value:
                            value = value.replace(expr, replacement)
                            setattr(node, attr_name, value)
                    elif isinstance(value, (dict, *config_classes)):
                        _replace_in_config(value, expr, replacement)

    def _replace_dict_items(*, node, prefix: str, this_path_prefix: str):
        for attr_name, value in node.items():
            prefix_attr = f"{prefix}.{attr_name}".lstrip('.')
            this_path = auto_path_prefixed(this_path_prefix, *attr_name.split('.'))
            if isinstance(value, str):
                if '{auto}' in value:
                    node[attr_name] = value.replace('{auto}', this_path)
                else:
                    expr = '{' + prefix_attr + '}'
                    _replace_in_config(parsed_config, expr, value)
            elif isinstance(value, dict):
                _replace_dict_items(node=value, prefix=prefix_attr, this_path_prefix=this_path)
            elif isinstance(value, config_classes):
                _replace_attrs(node=value, prefix=prefix_attr, this_path_prefix=this_path)

    def _replace_attrs(*, node, prefix: str, this_path_prefix: str):
        for attr_name in dir(node):
            if attr_name[0] != '_' and hasattr(node, attr_name):
                prefix_attr = f"{prefix}.{attr_name}".lstrip('.')
                this_path = this_path_prefix
                value = getattr(node, attr_name)
                if isinstance(value, str):
                    if '{auto}' in value:
                        setattr(node, attr_name, value.replace('{auto}', this_path))
                    else:
                        expr = '{' + prefix_attr + '}'
                        _replace_in_config(parsed_config, expr, value)
                elif isinstance(value, dict):
                    _replace_dict_items(node=value, prefix=prefix_attr, this_path_prefix=this_path)
                elif isinstance(value, config_classes):
                    _replace_attrs(node=value, prefix=prefix_attr, this_path_prefix=this_path)

    for _ in range(2):
        _replace_attrs(
            node=parsed_config,
            prefix='.',
            this_path_prefix=auto_prefix
        )
