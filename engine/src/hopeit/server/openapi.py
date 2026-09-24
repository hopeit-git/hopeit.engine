"""aiohttp request validation and documentation backed by openapi-core.

Only parameters and security are unmarshalled here. Payload schemas are validated
by hopeit's Pydantic deserializer, and multipart streams belong to preprocess hooks.
"""

import json
from collections.abc import Awaitable, Callable
from html import escape
from pathlib import Path
from typing import Any

from aiohttp import web
from jsonschema_path import SchemaPath
from openapi_core import OpenAPI
from openapi_core.casting.schemas import oas30_write_schema_casters_factory
from openapi_core.casting.schemas.casters import BooleanCaster, TypesCaster
from openapi_core.casting.schemas.factories import SchemaCastersFactory
from openapi_core.contrib.aiohttp import AIOHTTPOpenAPIWebRequest
from openapi_core.templating.paths.finders import BasePathFinder
from openapi_core.templating.paths.iterators import (
    SimpleOperationsIterator,
    SimplePathsIterator,
    SimpleServersIterator,
)
from openapi_core.unmarshalling.request.unmarshallers import (
    V30RequestParametersUnmarshaller,
    V30RequestSecurityUnmarshaller,
)
from openapi_core.validation.request.exceptions import MissingRequiredParameter

MULTIPART_FORM_FIELDS_KEY = "hopeit.multipart_form_fields"


class RequestValidationFailed(web.HTTPBadRequest):
    """Invalid OpenAPI request, with structured errors available to middleware."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(reason=json.dumps(errors))


class _RegisteredPathFinder(BasePathFinder):
    """aiohttp has already selected the route; public servers are documentation."""

    paths_iterator = SimplePathsIterator("paths")
    operations_iterator = SimpleOperationsIterator()
    servers_iterator = SimpleServersIterator()


class _StrictBooleanCaster(BooleanCaster):
    """Preserve hopeit's case-sensitive true/false wire representation."""

    def validate(self, value: Any) -> None:
        if not isinstance(value, bool) and value not in ("true", "false"):
            raise ValueError("expected true or false")


_default_casters = oas30_write_schema_casters_factory
_parameter_casters = SchemaCastersFactory(
    _default_casters.schema_validators_factory,
    TypesCaster(
        {**_default_casters.types_caster.casters, "boolean": _StrictBooleanCaster},
        _default_casters.types_caster.default,
    ),
)


def _validation_spec(spec: SchemaPath, path: str, method: str) -> SchemaPath:
    """Adapt parameter semantics without changing the published specification.

    Required parameters must be present even when their schema supplies a default.
    Empty query strings are values, subject to the schema's string constraints.
    Keep references rooted in the original document and operation overrides intact.
    """
    path_spec = spec / "paths" / path
    operation = path_spec / method

    def parameters(owner: SchemaPath) -> list[dict]:
        result = []
        for param in owner.get("parameters", []):
            value = dict(param.read_value())
            if "schema" in param:
                schema = dict((param / "schema").read_value())
                if value.get("required"):
                    schema.pop("default", None)
                if value["in"] == "query" and schema.get("type") == "string":
                    value["allowEmptyValue"] = True
                value["schema"] = schema
            result.append(value)
        return result

    document = dict(spec.read_value())
    document["paths"] = {
        **(spec / "paths").read_value(),
        path: {
            **path_spec.read_value(),
            "parameters": parameters(path_spec),
            method: {**operation.read_value(), "parameters": parameters(operation)},
        },
    }
    return SchemaPath.from_dict(document)


class _RouteRequest(AIOHTTPOpenAPIWebRequest):
    """Use the registered operation, including aiohttp's implicit HEAD on GET."""

    def __init__(self, request: web.Request, method: str, path: str):
        super().__init__(request, body=None)
        self.route_method = method
        self.route_path = path
        self.parameters.path = dict(request.match_info)

    @property
    def host_url(self) -> str:
        return ""

    @property
    def path(self) -> str:
        return self.route_path

    @property
    def method(self) -> str:
        return self.route_method


class OpenAPIRoute:
    """Validate a documented route without consuming multipart request bodies."""

    def __init__(
        self,
        method: str,
        path: str,
        handler: Callable[..., Awaitable[web.StreamResponse]],
        api: OpenAPI,
    ):
        self.method = method
        self.path = path
        self.handler = handler
        validation_spec = _validation_spec(api.spec, path, method)
        self.parameters = V30RequestParametersUnmarshaller(
            validation_spec,
            path_finder_cls=_RegisteredPathFinder,
            schema_casters_factory=_parameter_casters,
        )
        self.security = V30RequestSecurityUnmarshaller(
            validation_spec, path_finder_cls=_RegisteredPathFinder
        )
        self.body = (api.spec / "paths" / path / method).get("requestBody")
        self.form_fields: set[str] = set()
        if self.body is not None and "multipart/form-data" in self.body["content"]:
            schema = self.body / "content" / "multipart/form-data" / "schema"
            for name, field in schema.get("properties", {}).items():
                if (field / "format").read_str(default="") != "binary":
                    self.form_fields.add(name)

    async def handle(self, request: web.Request) -> web.StreamResponse:
        adapted = _RouteRequest(request, self.method, self.path)
        security = self.security.unmarshal(adapted)
        if security.errors:
            raise RequestValidationFailed({"authorization": str(next(iter(security.errors)))})
        result = self.parameters.unmarshal(adapted)
        if result.errors:
            raise RequestValidationFailed(
                {
                    getattr(error, "name", "parameters"): (
                        "is required" if isinstance(error, MissingRequiredParameter) else str(error)
                    )
                    for error in result.errors
                }
            )
        data: dict[str, Any] = dict(security.security or {})
        for location in ("query", "header", "path", "cookie"):
            data.update(getattr(result.parameters, location))
        request["data"] = data
        if self.body is not None:
            if not request.body_exists:
                if (self.body / "required").read_bool(default=False):
                    raise RequestValidationFailed({"body": "is required"})
                data["body"] = None
            elif request.content_type not in self.body["content"]:
                raise RequestValidationFailed({"body": f"no handler for {request.content_type}"})
            elif request.content_type == "multipart/form-data":
                request[MULTIPART_FORM_FIELDS_KEY] = self.form_fields
                data["body"] = request
            elif request.content_type == "application/json":
                try:
                    data["body"] = await request.json()
                except (ValueError, UnicodeError) as error:
                    raise RequestValidationFailed({"body": "invalid JSON"}) from error
        return await self.handler(request)


def setup_docs(app: web.Application, spec: dict, docs_path: str) -> None:
    """Serve Swagger UI and the spec locally, independently of request validation."""
    path = docs_path.rstrip("/")
    title = escape(spec["info"]["title"])
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="./swagger_ui_static/favicon-32x32.png">
<link rel="stylesheet" href="./swagger_ui_static/swagger-ui.css">
<script defer src="./swagger_ui_static/swagger-ui-bundle.js"></script>
<script defer src="./swagger_ui_static/initializer.js"></script>
</head><body>
<div id="swagger-ui"></div>
</body></html>"""

    async def docs(request: web.Request) -> web.Response:
        return web.Response(text=html, content_type="text/html")

    async def specification(request: web.Request) -> web.Response:
        return web.json_response(spec)

    async def redirect(request: web.Request) -> web.StreamResponse:
        target = request.rel_url.with_path(f"{request.path}/").with_query(request.query)
        raise web.HTTPPermanentRedirect(location=str(target))

    if path:
        app.router.add_get(path, redirect)
    app.router.add_get(f"{path}/", docs)
    app.router.add_get(f"{path}/swagger.json", specification)
    app.router.add_static(
        f"{path}/swagger_ui_static", Path(__file__).parent / "static" / "swagger_ui"
    )
