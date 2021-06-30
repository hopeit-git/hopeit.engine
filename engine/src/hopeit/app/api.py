"""
API Definition helpers for user apps
"""
import inspect
from functools import partial
from typing import Optional, List, Type, Dict, Callable, Union, Tuple, Any, TypeVar

import re
import typing_inspect  # type: ignore

from hopeit.dataobjects import BinaryDownload
from hopeit.app.config import AppConfig, AppDescriptor, EventType
from hopeit.server.api import spec, app_route_name, APIError, BUILTIN_TYPES, datatype_schema
from hopeit.server.names import route_name

__all__ = ['api_from_config',
           'event_api',
           'app_base_route_name']

ArgType = TypeVar("ArgType", bound=Type)
ArgDef = Union[str, Tuple[str, ArgType], Tuple[str, ArgType, str]]
PayloadDef = Union[Type, Tuple[Type, str]]


def api_from_config(module, *, app_config: AppConfig, event_name: str, plugin: Optional[AppConfig]) -> dict:
    """
    Uses api definition exactly as it comes from --api-file specified at runtime.

    Usage in app event implementation file::

        __api__ = api_from_config

    Notice that no arguments need to be provided (just the function) as the function will be invoked
    during server initialization.
    """
    assert spec is not None
    plugin_app = None if plugin is None else plugin.app
    override_route_name = app_config.events[event_name].route
    route = app_route_name(app_config.app, event_name=event_name, plugin=plugin_app,
                           override_route_name=override_route_name)
    method = app_config.events[event_name].type.value.lower()
    event_spec = spec['paths'].get(route)
    if event_spec is None:
        raise APIError(f"Missing API Config for app={app_config.app.app_key()} event={event_name}")
    method_spec = event_spec.get(method)
    if method_spec is None:
        raise APIError(f"Missing method={method} for app={app_config.app.app_key()} event={event_name}")
    return event_spec[method]


def app_base_route_name(app: AppDescriptor, *, plugin: Optional[AppDescriptor] = None, prefix='api') -> str:
    """
    Returns base route name for paths in a given app
    """
    components = [
        prefix, app.name, app.version,
        *([plugin.name, plugin.version] if plugin else [])
    ]
    return route_name(*components)


def _arg_name(arg: ArgDef) -> str:
    if isinstance(arg, str):
        return arg
    return arg[0]


def _arg_type(arg: ArgDef) -> Tuple[str, Optional[str], bool]:
    if isinstance(arg, str):
        return (*BUILTIN_TYPES[str], True)
    datatype, required = arg[1], True
    origin = typing_inspect.get_origin(datatype)
    if origin is Union:
        type_args = typing_inspect.get_args(datatype)
        datatype = type_args[0]
        required = type_args[-1] is None
    return (*BUILTIN_TYPES.get(datatype, BUILTIN_TYPES[str]), required)


def _arg_description(arg: ArgDef) -> str:
    if isinstance(arg, str):
        return arg
    if len(arg) == 3:
        return arg[2]  # type: ignore
    return arg[0]


def _payload_schema(event_name: str, arg: PayloadDef) -> dict:
    datatype = arg[0] if isinstance(arg, tuple) else arg
    return datatype_schema(event_name, datatype)


def _payload_description(arg: PayloadDef) -> str:
    if isinstance(arg, tuple):
        return arg[1]
    if hasattr(arg, '__name__'):
        return arg.__name__
    return str(arg)


def _method_summary(module: str, summary: Optional[str] = None) -> str:
    if summary is not None:
        return summary
    doc_str = inspect.getdoc(module)
    if doc_str is not None:
        return doc_str.split("\n", maxsplit=1)[0]
    return ""


def _method_description(module: str, description: Optional[str] = None, summary: Optional[str] = None) -> str:
    if description is not None:
        return description
    doc_str = inspect.getdoc(module)
    if doc_str is not None and doc_str.count('\n') > 1:
        return re.sub(r"^\W+", "", doc_str.split("\n", 1)[1])
    return _method_summary(module, summary)


def _parse_args_schema(query_args: Optional[List[ArgDef]]):
    """
    Parse query args schema
    """
    parameters = []
    for query_arg in (query_args or []):
        arg_name = _arg_name(query_arg)
        arg_type, arg_format, arg_req = _arg_type(query_arg)
        arg_desc = _arg_description(query_arg)
        arg_spec: dict = {
            "name": arg_name,
            "in": "query",
            "required": arg_req,
            "description": arg_desc,
            "schema": {
                "type": arg_type
            }
        }
        if arg_format is not None:
            arg_spec["schema"]["format"] = arg_format
        parameters.append(arg_spec)
    return parameters


def _parse_fields_schema(fields: Optional[List[ArgDef]]):
    """
    Parse form fields schema
    """
    fields_schema = {"type": "object", "required": [], "properties": {}}
    encoding = {}
    for field in (fields or []):
        arg_name = _arg_name(field)
        arg_type = str if len(field) == 1 else field[1]
        arg_schema = datatype_schema(arg_name, arg_type)  # type: ignore
        fields_schema['required'].append(arg_name)  # type: ignore
        props = arg_schema.get('properties', {arg_name: arg_schema})
        fields_schema['properties'].update(props)  # type: ignore
        if props[arg_name].get('type') == 'string':
            encoding[arg_name] = {
                'contentType':
                'application/octect-stream' if props[arg_name].get('format') == 'binary' else 'text/plain'
            }
        else:
            encoding[arg_name] = {'contentType': 'application/json'}
        arg_desc = _arg_description(field)
        if arg_desc is not None:
            fields_schema['properties'][arg_name]['description'] = arg_desc  # type: ignore
    return fields_schema, encoding


def _event_api(
        summary: Optional[str],
        description: Optional[str],
        payload: Optional[Type],
        query_args: Optional[List[ArgDef]],
        fields: Optional[List[ArgDef]],
        responses: Optional[Dict[int, PayloadDef]],
        module, app_config: AppConfig, event_name: str, plugin: Optional[AppConfig]) -> dict:
    """
    Handler returned by event_api(...)
    """
    parameters = _parse_args_schema(query_args)

    method_spec: Dict[str, Any] = {
        "summary": _method_summary(module, summary),
        "description": _method_description(module, description, summary),
        "parameters": parameters
    }

    event_config = app_config.events[event_name]
    content_type = 'multipart/form-data' if event_config.type == EventType.MULTIPART else 'application/json'
    if payload is not None:
        method_spec['requestBody'] = {
            "description": _payload_description(payload),
            "required": True,
            "content": {
                content_type: {
                    "schema": _payload_schema(event_name, payload)
                }
            }
        }

    def _payload_content_type(arg: PayloadDef) -> Tuple[PayloadDef, str]:
        dt = arg[0] if isinstance(arg, tuple) else arg
        if inspect.isclass(dt) and issubclass(dt, BinaryDownload):
            return (BinaryDownload, arg[1]) if isinstance(arg, tuple) else BinaryDownload, dt.content_type
        return arg, "application/json"

    def _response_content(datatype) -> dict:
        dt, content_type = _payload_content_type(datatype)
        return {content_type: {
                "schema": _payload_schema(event_name, dt)}}

    if fields is not None:
        if payload is not None:
            raise APIError("Payload and fields cannot be specified at the same time.")

        method_schema, encoding = _parse_fields_schema(fields)
        method_spec['requestBody'] = {
            "required": True,
            "content": {
                content_type: {
                    "schema": method_schema,
                    "encoding": encoding
                }
            }
        }

    api_responses = {
        str(status): {
            "description": _payload_description(datatype),
            "content": _response_content(datatype)
        } for status, datatype in (responses or {}).items()}
    method_spec['responses'] = api_responses
    return method_spec


def event_api(*, summary: Optional[str] = None,
              description: Optional[str] = None,
              payload: Optional[PayloadDef] = None,
              query_args: Optional[List[ArgDef]] = None,
              fields: Optional[List[ArgDef]] = None,
              responses: Optional[Dict[int, PayloadDef]] = None) -> Callable[..., dict]:
    """
    Provides a convenient way to define Open API specification using Python types for a given app event
    implementation module.

    :param summary: An optional, string summary. If not provided will be taken from module docstring first line.
    :param description: An optional, string description. If not provided will be taken from module docstring.
    :param payload: Payload schema definition. Could be a single data type, or a tuple with a Type and a description.
    :param query_args: List of query arguments: each argument could be a single string with the arg name (in which case
        str type will be assumed), or a tuple of (str, type), where type if a valid datatype for query args (str, int,
        float, bool), or a tuple of (str, type, str) where last string is argument description.
    :param responses: a dictionary where key HTTP status code and value is the payload definition as describer in
        payload parameter.

    Examples:

    This will generate Open Schema with default types and description::

        __api__ = event_api(payload=CustomDataType, query_args['arg1'], responses={200: CustomResultDataType})

    Types and descriptions can be defined more precisely, and multiple response types can be specified::

        __api__ = event_api(
            payload=(CustomDataType, "A CustomDataType object to be used as an input"),
            query_args[('arg1', str, "Argument expected in query string",
            responses: {
                200: (CustomResultDataType, "Result in case operation is successful"),
                404: (NotFoundInformation, "Information return in case object is not found")
            }
        )
    """

    return partial(_event_api, summary, description, payload, query_args, fields, responses)
