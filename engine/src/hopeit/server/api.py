"""
Open API spec creation and server helpers
"""
import json
import re
from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import Dict, List, Tuple, Type, Optional, Callable, Awaitable, Union

from aiohttp import web
from aiohttp_swagger3 import RapiDocUiSettings  # type: ignore
from aiohttp_swagger3.swagger import Swagger  # type: ignore
from aiohttp_swagger3.exceptions import ValidatorError  # type: ignore
from aiohttp_swagger3 import validators  # type: ignore
from aiohttp_swagger3.validators import MISSING, _MissingType  # type: ignore
from aiohttp_swagger3.swagger_route import SwaggerRoute  # type: ignore
from stringcase import titlecase  # type: ignore
import typing_inspect as typing  # type: ignore
from dataclasses_jsonschema import SchemaType

from hopeit.dataobjects import BinaryAttachment, BinaryDownload  # type: ignore
from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, EventPlugMode, EventType
from hopeit.server.config import ServerConfig, AuthType
from hopeit.server.errors import ErrorInfo
from hopeit.server.imports import find_event_handler
from hopeit.server.logger import engine_logger
from hopeit.server.names import route_name
from hopeit.server.steps import extract_module_steps, extract_postprocess_handler, extract_preprocess_handler, \
    StepInfo


__all__ = ['init_empty_spec',
           'load_api_file',
           'save_api_file',
           'setup',
           'clear',
           'app_route_name',
           'register_server_config',
           'register_apps',
           'enable_swagger',
           'diff_specs']

logger = engine_logger()

swagger: Optional[Swagger] = None
spec: Optional[dict] = None
static_spec: Optional[dict] = None
runtime_schemas = {}
_options = {
    'generate_mode': False
}

OPEN_API_VERSION = '3.0.3'

METHOD_MAPPING = {
    EventType.GET: 'get',
    EventType.POST: 'post',
    EventType.MULTIPART: 'post'
}


class APIError(Exception):
    """
    Error thrown when API incompatibilities are detected
    """


def setup(**kwargs):
    """
    Setup additional options for api module. Supported options are:

    :param generate_mode: bool, default False: creates empty path placholders for modules not defining __api__
        specification
    """
    _options.update(**kwargs)


def clear():
    """
    Clears api configuration stored in memory. This disables api module.
    """
    global spec, static_spec, swagger, runtime_schemas, _options
    spec = None
    static_spec = None
    swagger = None
    runtime_schemas = {}
    _options = {
        'generate_mode': False
    }


def init_empty_spec(api_version: str, title: str, description: str):
    """
    Initializes internal spec and static_spec dictionaries with minimal Open API requirements:
    openapi, info sections and empty paths. This method can be used to create new API specs.
    :param api_version: info.version
    :param title: info.title
    :param description: info.description
    """
    global spec, static_spec
    logger.info(__name__, "Creating Open API spec...")
    spec = {
        "openapi": OPEN_API_VERSION,
        "info": {
            "version": api_version,
            "title": title,
            "description": description
        },
        "paths": {}
    }
    logger.info(__name__, f"API: openapi={spec['openapi']}, API version={spec['info']['version']}")
    static_spec = deepcopy(spec)


def load_api_file(path: Union[str, Path]):
    """
    Loads OpenAPI spec from a json file. Spec is loaded into the module.
    @param path: path to json file
    """
    global spec, static_spec
    logger.info(__name__, f"Loading api spec from api_file={path}...")
    with open(path, 'r') as f:
        spec = json.loads(f.read())
        assert spec is not None
        logger.info(__name__, f"API: openapi={spec['openapi']}, API version={spec['info']['version']}")
        static_spec = deepcopy(spec)


def save_api_file(path: Union[str, Path], api_version: str):
    """
    Saves module Open API spec to json file.
    :param path: path to json file
    :param api_version: new api_version, in case changes between previously loaded api file and api calculated at
        runtime, a new api_version needs to be specified to allow saving the file.
    """
    assert spec is not None
    assert static_spec is not None
    if diff_specs() and static_spec['info']['version'] == api_version:
        err = APIError("Cannot save api file. Need to increment version number. Differences found.")
        logger.error(__name__, err)
        raise err
    logger.info(__name__, f"Set API version={api_version}...")
    spec['info']['version'] = api_version
    logger.info(__name__, f"Saving api spec to api_file={path}...")
    with open(path, 'w') as f:
        f.write(json.dumps(spec, indent=2))
        f.flush()


def register_server_config(server_config: ServerConfig):
    """
    Register API definitions from server configuration. This consists of allowed and default authentication methods.
    """
    if spec is not None:
        if 'components' not in spec:
            spec['components'] = {'schemas': {}}
        _update_auth_methods()
        _update_server_default_auth_methods(server_config)


def register_apps(apps_config: List[AppConfig]):
    """
    Register api definition for a list of apps that conform to a single API specification.

    @param apps_config: list of AppConfig objects to be introspected
    """
    if spec is not None:
        logger.info(__name__, "Registering apps...")
        apps_config_by_key = {config.app.app_key(): config for config in apps_config}
        for config in apps_config:
            logger.info(__name__, f"Updating API spec for app={config.app_key()}...")
            _register_api_spec(config)
            for plugin in config.plugins:
                logger.info(__name__, f"Updating API spec for app={config.app_key()}, plugin={plugin.app_key()}...")
                plugin_config = apps_config_by_key[plugin.app_key()]
                _register_api_spec(config, plugin_config)
        _cleanup_api_schemas()


def _register_api_spec(app_config: AppConfig, plugin: Optional[AppConfig] = None):
    if spec is not None:
        if 'components' not in spec:
            spec['components'] = {'schemas': {}}
        _update_predefined_schemas()
        _update_api_schemas(app_config)
        _update_api_paths(app_config, plugin)


def diff_specs() -> bool:
    """
    Detects differences between loaded API specification and spec calculated from server and apps.

    :return: True if differences are found, False if loaded spec matches runtime.
    """
    return static_spec != spec


async def _passthru_handler(request: web.Request) -> Tuple[web.Request, bool]:
    return request, True


class CustomizedObjectValidator(validators.Object):  # pragma: no cover
    """
    Replacements of Object Validator provided by aiohttp3_swagger
    to handle multipart form requests
    """
    def validate(self, raw_value: Union[None, Dict, _MissingType],
                 raw: bool) -> Union[None, Dict, _MissingType]:
        # FIXED: is_missing = isinstance(raw_value, _MissingType)
        is_missing = (
            isinstance(raw_value, _MissingType)
            or ((raw_value is not None) and (not isinstance(raw_value, dict)))
        )
        # ORIGINAL CODE: https://github.com/hh-h/aiohttp-swagger3/blob/master/aiohttp_swagger3/validators.py
        # FIXED END
        if not is_missing and self.readOnly:
            raise ValidatorError("property is read-only")
        if raw_value is None:
            if self.nullable:
                return None
            raise ValidatorError("value should be type of dict")
        if not isinstance(raw_value, dict):
            if is_missing:
                return raw_value
            raise ValidatorError("value should be type of dict")
        value = {}
        errors: Dict = {}
        for name in self.required:
            if name not in raw_value:
                errors[name] = "required property"
        if errors:
            raise ValidatorError(errors)

        for name, validator in self.properties.items():
            prop = raw_value.get(name, MISSING)
            try:
                val = validator.validate(prop, raw)
                if val != MISSING:
                    value[name] = val
            except ValidatorError as e:
                errors[name] = e.error
        if errors:
            raise ValidatorError(errors)

        if isinstance(self.additionalProperties, bool):
            if not self.additionalProperties:
                additional_properties = raw_value.keys() - value.keys()
                if additional_properties:
                    raise ValidatorError({k: "additional property not allowed" for k in additional_properties})
            else:
                for key in raw_value.keys() - value.keys():
                    value[key] = raw_value[key]
        else:
            for name in raw_value.keys() - value.keys():
                validator = self.additionalProperties
                value[name] = validator.validate(raw_value[name], raw)
        if self.minProperties is not None and len(value) < self.minProperties:
            raise ValidatorError(f"number or properties must be more than {self.minProperties}")
        if self.maxProperties is not None and len(value) > self.maxProperties:
            raise ValidatorError(f"number or properties must be less than {self.maxProperties}")
        return value


setattr(validators.Object, "validate", CustomizedObjectValidator.validate)


def enable_swagger(server_config: ServerConfig, app: web.Application):
    """
    Enables Open API (a.k.a Swagger) on this server. This consists of:
        * All endpoints within API specification are to be handled by a Open API handler that will validate requests
        * If specified in server_config.api_docs_path, API docs site will be available at the given route.
            i.e. http://server-address:8020/api/docs
    :param server_config: server configuration
    :param app: aiohttp web Application to host routes and docs
    """
    global swagger, static_spec
    if spec is None:
        logger.warning(__name__, "No api-file loaded. OpenAPI docs and validation disabled.")
        return
    if diff_specs():
        err = APIError("Cannot enable OpenAPI. Differences found between api-file and running apps. "
                       "Run `hopeit openapi diff` to check and `hopeit openapi update` to generate spec file")
        logger.error(__name__, err)
        raise err
    static_spec = None
    logger.info(__name__, "Enabling OpenAPI endpoints...")
    app["AIOHTTP_SWAGGER3_SWAGGER_SPECIFICATION"] = spec
    api_docs_ui = None
    if server_config.api.docs_path:
        api_docs_ui = RapiDocUiSettings(
            path=server_config.api.docs_path,
            heading_text=spec['info']['title'],
            theme='dark',
            render_style='read',
            layout='column',
            schema_style='tree',
            allow_spec_url_load=False,
            allow_spec_file_load=False,
            allow_server_selection=False,
            show_header=False
        )
        logger.info(__name__, f"OpenAPI documentation available in {server_config.api.docs_path}")
    else:
        logger.warning(
            __name__, "OpenAPI documentation path not specified in server config. API docs endpoint disabled.")

    swagger = Swagger(
        app,
        validate=True,
        spec=spec,
        request_key="data",
        rapidoc_ui_settings=api_docs_ui,
        redoc_ui_settings=None,
        swagger_ui_settings=None
    )
    swagger.register_media_type_handler("multipart/form-data", _passthru_handler)
    logger.info(__name__, "OpenAPI validations enabled.")


def add_route(method: str,
              path: str,
              handler: Callable[..., Awaitable[web.StreamResponse]]) -> Callable[..., Awaitable[web.StreamResponse]]:
    """
    Register a route handler. In case the path is associated with a path in Open API running spec,
    handler is to be wrapped by an Open API handler, if not, handler will be returned with no changes
    and a WARNING is logged.

    :param method: str, valid Open API method (i.e. GET, POST)
    :param path: str, route
    :param handler: function to be used as handler
    """
    if spec is None:
        return handler
    assert swagger is not None, "API module not initialized. Call `api.enable_swagger(...)`"
    method_lower = method.lower()
    if method_lower in spec["paths"].get(path, {}):
        route = SwaggerRoute(method_lower, path, handler, swagger=swagger)
        api_handler = partial(swagger._handle_swagger_call, route)  # pylint: disable=protected-access
        return api_handler
    logger.warning(__name__, f"No API Spec defined for path={path}")
    return handler


def app_route_name(app: AppDescriptor, *, event_name: str,
                   plugin: Optional[AppDescriptor] = None,
                   prefix: str = 'api', override_route_name: Optional[str] = None) -> str:
    """
    Returns the full route name for a given app event

    :param app: AppDescriptor, as defined in AppConfig
    :param event_name: event name as defined in AppConfig
    :param plugin: optional plugin if the event comes from a plugin and EventPlugMode=='OnApp'
    :param prefix: route prefix, defaults to 'api'
    :param override_route_name: Optional[str], provided route to be used instead app and event name
    :return: str, full route name. i.e.:
        /api/app-name/1x0/event-name or /api/app-name/1x0/plugin-name/1x0/event-name
    """
    components = [
        prefix, app.name, app.version,
        *([plugin.name, plugin.version] if plugin else []),
        *event_name.split('.')
    ] if override_route_name is None else [
        prefix, override_route_name
    ]
    return route_name(*components)


def _schema_name(datatype: type) -> str:
    return f"#/components/schemas/{datatype.__name__}"


def datatype_schema(event_name: str, datatype: Type) -> dict:
    origin = typing.get_origin(datatype)
    if origin is None:
        origin = datatype
    type_mapper = TYPE_MAPPERS.get(origin)
    if type_mapper is None:
        return {
            "$ref": _schema_name(datatype)
        }
    return type_mapper(event_name, datatype)  # type: ignore


def _update_auth_methods():
    """
    Generate default securitySchemes section
    """
    security_schemas = spec['components'].get('securitySchemes', {})
    security_schemas.update({
        'auth.basic': {
            'type': 'http',
            'scheme': 'basic'
        },
        'auth.bearer': {
            'type': 'http',
            'scheme': 'bearer'
        }
    })
    spec['components']['securitySchemes'] = security_schemas


def _update_auth_refresh_method(app_key: str):
    """
    Generate securitySchemes entries for REFRESH token cookie for each app
    """
    assert spec is not None
    security_schemas = spec['components'].get('securitySchemes', {})
    security_schemas.update({
        f"{app_key}.refresh": {
            'type': 'apiKey',
            'in': 'cookie',
            'name': f"{app_key}.refresh"
        }
    })
    spec['components']['securitySchemes'] = security_schemas


def _update_server_default_auth_methods(server_config: ServerConfig):
    """
    Generate security section based on server default_auth_methods
    """
    assert spec is not None
    security = spec.get('security', [])
    methods = {method for entry in security for method in entry.keys()}
    for auth_method in server_config.auth.default_auth_methods:
        auth_str = f"auth.{auth_method.value.lower()}"
        if auth_str != 'auth.unsecured' and auth_str not in methods:
            security.append({auth_str: []})
    spec['security'] = security


def _update_api_schemas(app_config: AppConfig):
    """
    Generate schemas for @dataobject annotated dataclasses discovered in event implementation modules
    """
    assert spec is not None
    schemas = spec['components'].get('schemas', {})
    for event_name in app_config.events.keys():
        event_schemas = _generate_schemas(app_config, event_name)
        for name, event_schema in event_schemas.items():
            if name in runtime_schemas:
                if not event_schema == schemas.get(name):
                    logger.warning(__name__,
                                   f"Schema ignored: same schema name has non-compatible implementations: "
                                   f"event={event_name} schema={name}")
            else:
                schemas[name] = event_schema
                runtime_schemas[name] = event_schema

    spec['components']['schemas'] = schemas


def _update_predefined_schemas():
    """
    Generate schemas for predefined classes
    """
    assert spec is not None
    spec['components']['schemas'].update(
        ErrorInfo.json_schema(schema_type=SchemaType.V3, embeddable=True)
    )


def _cleanup_api_schemas():
    """
    Remove schemas from spec, if they are not used in paths
    """
    assert spec is not None
    modified = True
    while modified:
        clean = {}
        spec_str = json.dumps(spec)
        schemas = spec['components'].get('schemas', {})
        for name, schema in schemas.items():
            if spec_str.find(f"#/components/schemas/{name}") >= 0:
                clean[name] = schema
        modified = len(schemas) > len(clean)
        spec['components']['schemas'] = clean


def _update_api_paths(app_config: AppConfig, plugin: Optional[AppConfig] = None):
    """
    Populates paths section of spec based on __api__ specified in implemented events
    """
    assert spec is not None
    events = {
        k: v for k, v in app_config.events.items() if v.plug_mode == EventPlugMode.STANDALONE
    } if plugin is None else {
        k: v for k, v in plugin.events.items() if v.plug_mode == EventPlugMode.ON_APP
    }
    plugin_app = None if plugin is None else plugin.app
    paths = spec.get('paths', {})
    for event_name, event_info in events.items():
        route = app_route_name(app_config.app, event_name=event_name, plugin=plugin_app,
                               override_route_name=event_info.route)
        method = METHOD_MAPPING.get(event_info.type)
        if method is None:
            continue
        event_api_spec = _extract_event_api_spec(app_config if plugin is None else plugin, event_name)
        if event_api_spec is None:
            event_api_spec = paths.get(route, {}).get(method)
        if event_api_spec is None and _options.get('generate_mode'):
            event_api_spec = {"description": f"<<<{event_name}>>>", "parameters": [], "responses": {}}
        if event_api_spec is not None:
            event_api_spec['tags'] = [app_config.app_key()]
            _set_optional_fixed_headers(event_api_spec)
            _set_track_headers(event_api_spec, app_config)
            _set_path_security(event_api_spec, app_config, event_info)
            route_path = paths.get(route, {})
            route_path[method] = event_api_spec
            paths[route] = route_path
    spec['paths'] = paths


def _set_optional_fixed_headers(event_api_spec: dict):
    """
    Set arguments for request-id and request-ts track headers on every path entry
    """
    if not any(param['name'] == 'X-Track-Request-Id' for param in event_api_spec['parameters']):
        event_api_spec['parameters'].append({
            "name": "X-Track-Request-Id",
            "in": "header",
            "required": False,
            "description": "Track information: Request-Id",
            "schema": {
                "type": "string"
            }
        })
    if not any(param['name'] == 'X-Track-Request-Ts' for param in event_api_spec['parameters']):
        event_api_spec['parameters'].append({
            "name": "X-Track-Request-Ts",
            "in": "header",
            "required": False,
            "description": "Track information: Request-Ts",
            "schema": {
                "type": "string",
                "format": "date-time"
            }
        })


def _set_track_headers(event_api_spec: dict, app_config: AppConfig):
    """
    Set arguments for track headers specified in app_config for every path
    """
    current_params = {entry['name'] for entry in event_api_spec['parameters']}
    for track_header in app_config.engine.track_headers:
        header_name = f"X-{re.sub(' ', '-', titlecase(track_header))}"
        if header_name not in current_params:
            event_api_spec['parameters'].append({
                "name": header_name,
                "in": "header",
                "required": True,
                "description": f"Track information: {track_header}",
                "schema": {
                    "type": "string",
                    "default": track_header.replace('track', 'test')
                }
            })


def _set_path_security(event_api_spec: dict, app_config: AppConfig, event_info: EventDescriptor):
    """
    Setup security schemes allowed for each path
    """
    assert spec is not None
    security: list = []
    for auth in event_info.auth:
        if auth == AuthType.REFRESH:
            _update_auth_refresh_method(app_config.app_key())
            auth_str = f"{app_config.app_key()}.refresh"
            security.append({auth_str: []})
        elif auth != AuthType.UNSECURED:
            auth_str = f"auth.{auth.value.lower()}"
            security.append({auth_str: []})
    if len(security) == 0:
        security = spec['security']
    if len(security) > 0:
        event_api_spec['security'] = security


def _extract_event_api_spec(app_config: AppConfig, event_name: str) -> Optional[dict]:
    """
    Extract __api__ definition from event implementation
    """
    module = find_event_handler(app_config=app_config, event_name=event_name)
    if hasattr(module, '__api__'):
        method_spec = getattr(module, '__api__')
        if isinstance(method_spec, dict):
            return method_spec
        return method_spec(module, app_config, event_name, None)
    return None


def _generate_schemas(app_config: AppConfig, event_name: str) -> dict:
    """
    Generate all schemas for a given event, based on steps signatures
    """
    module = find_event_handler(app_config=app_config, event_name=event_name)
    steps = extract_module_steps(module)
    schemas: dict = {}
    for _, step_info in steps:
        _update_step_schemas(schemas, step_info)
    step_info = extract_postprocess_handler(module)
    _update_step_schemas(schemas, step_info)
    step_info = extract_preprocess_handler(module)
    _update_step_schemas(schemas, step_info)
    return schemas


def _update_step_schemas(schemas: dict, step_info: Optional[StepInfo]):
    if step_info is not None:
        _, input_type, ret_type = step_info
        datatypes = _explode_datatypes([input_type, ret_type])
        for datatype in datatypes:
            if datatype is not None and hasattr(datatype, '__data_object__'):
                if datatype.__data_object__['schema']:
                    schemas.update(datatype.json_schema(schema_type=SchemaType.V3, embeddable=True))


def _explode_datatypes(datatypes: List[Type]) -> List[Type]:
    result = []
    for datatype in datatypes:
        if datatype is not None:
            if hasattr(datatype, '__args__'):
                for arg in getattr(datatype, '__args__'):
                    result.extend(_explode_datatypes([arg]))
            else:
                result.append(datatype)
    return result


def _array_schema(event_name: str, datatype: type):
    args = typing.get_args(datatype)
    return {
        "type": "array",
        "items": {
            "$ref": _schema_name(args[0])
        }
    }


def _binary_download_schema(event_name: str, datatype: type):
    return {
        "type": "string",
        "format": "binary"
    }


def _builtin_schema(type_name: str, type_format: Optional[str],
                    event_name: str, datatype: type) -> dict:
    """
    Build type schema for predefined datatypes
    """
    schema = {
        "type": "object",
        "required": [
            event_name
        ],
        "properties": {
            event_name: {
                "type": type_name,
            }
        },
        "description": f"{event_name} {type_name} payload"
    }
    if type_format is not None:
        schema['properties'][event_name]['format'] = type_format  # type: ignore
    return schema


TYPE_MAPPERS = {
    str: partial(_builtin_schema, 'string', None),
    int: partial(_builtin_schema, 'integer', None),
    float: partial(_builtin_schema, 'number', None),
    bool: partial(_builtin_schema, 'boolean', None),
    list: _array_schema,
    BinaryAttachment: partial(_builtin_schema, 'string', 'binary'),
    BinaryDownload: _binary_download_schema
}

BUILTIN_TYPES = {
    str: 'string',
    int: 'integer',
    float: 'number',
    bool: 'boolean'
}
