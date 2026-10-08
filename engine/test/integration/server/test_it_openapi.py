"""Exercise OpenAPI validation through real aiohttp requests."""

from copy import deepcopy

import aiohttp
import pytest
from aiohttp import web
from hopeit.app.context import PreprocessHook
from hopeit.server import api
from hopeit.server.config import APIConfig, ServerConfig
from hopeit.server.openapi import MULTIPART_FORM_FIELDS_KEY
from mock_app import mock_api_app_config


@pytest.fixture
def specification():
    return {
        "openapi": "3.0.4",
        "info": {"title": "Validation <test>", "version": "1.0"},
        "paths": {
            "/items/{item}": {
                "parameters": [
                    {"name": "item", "in": "path", "required": True, "schema": {"type": "integer"}},
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "count",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1},
                        },
                        {
                            "name": "tags",
                            "in": "query",
                            "schema": {"type": "array", "items": {"type": "string"}},
                        },
                        {
                            "name": "X-Test",
                            "in": "header",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "session",
                            "in": "cookie",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/payload": {
                "post": {
                    "requestBody": {"$ref": "#/components/requestBodies/Payload"},
                    "responses": {"200": {"description": "OK"}},
                },
            },
        },
        "components": {
            "securitySchemes": {
                "bearer": {"type": "http", "scheme": "bearer"},
                "basic": {"type": "http", "scheme": "basic"},
                "refresh": {"type": "apiKey", "in": "cookie", "name": "refresh"},
            },
            "requestBodies": {
                "Payload": {
                    "required": True,
                    "content": {
                        "application/json": {"schema": {"type": "object"}},
                        "multipart/form-data": {"schema": {"type": "object"}},
                    },
                },
            },
        },
    }


async def make_client(aiohttp_client, specification, handler, docs_path="/api/docs"):
    api.clear()
    api.spec = deepcopy(specification)
    app = web.Application()
    api.enable_swagger(ServerConfig(api=APIConfig(docs_path=docs_path)), app)
    app.router.add_get("/items/{item}", api.add_route("GET", "/items/{item}", handler))
    app.router.add_post("/payload", api.add_route("POST", "/payload", handler))
    client = await aiohttp_client(app)
    # Registered handlers must retain their own spec, independently of module state.
    api.clear()
    return client


async def echo(request):
    return web.json_response(request["data"])


async def test_parameters(aiohttp_client, specification):
    client = await make_client(aiohttp_client, specification, echo)
    headers = {"x-test": "header", "Cookie": "session=cookie"}
    response = await client.get("/items/7?count=2&tags=a&tags=b", headers=headers)
    assert response.status == 200
    assert await response.json() == {
        "item": 7,
        "count": 2,
        "tags": ["a", "b"],
        "X-Test": "header",
        "session": "cookie",
    }
    response = await client.head("/items/7?count=2", headers=headers)
    assert response.status == 200
    for url, request_headers in [
        ("/items/7", headers),
        ("/items/7?count=invalid", headers),
        ("/items/7?count=0", headers),
        ("/items/invalid?count=1", headers),
        ("/items/7?count=1", {"Cookie": "session=cookie"}),
        ("/items/7?count=1", {"X-Test": "header"}),
    ]:
        response = await client.get(url, headers=request_headers)
        assert response.status == 400, await response.text()


@pytest.mark.parametrize(
    "security,headers",
    [
        ({"bearer": []}, {"Authorization": "Bearer token"}),
        ({"basic": []}, {"Authorization": "Basic dXNlcjpwYXNz"}),
        ({"refresh": []}, {"Cookie": "refresh=token"}),
    ],
)
async def test_security(aiohttp_client, specification, security, headers):
    specification["paths"]["/payload"]["post"]["security"] = [security]
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.post("/payload", json={})
    assert response.status == 400
    response = await client.post("/payload", json={}, headers=headers)
    assert response.status == 200, await response.text()


async def test_json_body(aiohttp_client, specification):
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.post("/payload", json={"value": "ok"})
    assert response.status == 200
    assert (await response.json())["body"] == {"value": "ok"}
    for kwargs in [
        {},
        {"data": "text"},
        {"data": "{invalid", "headers": {"Content-Type": "application/json"}},
    ]:
        response = await client.post("/payload", **kwargs)
        assert response.status == 400


@pytest.mark.parametrize("content_type", ["application/merge-patch+json", "text/plain"])
async def test_unsupported_documented_body(aiohttp_client, specification, content_type):
    specification["components"]["requestBodies"]["Payload"]["content"][content_type] = {
        "schema": {"type": "string"}
    }

    async def unexpected_handler(request):
        pytest.fail("Unsupported body must be rejected before calling the handler")

    client = await make_client(aiohttp_client, specification, unexpected_handler)
    response = await client.post(
        "/payload", data='{"value":"ok"}', headers={"Content-Type": content_type}
    )
    assert response.status == 400
    assert f"no handler for {content_type}" in await response.text()


async def test_optional_body(aiohttp_client, specification):
    specification["components"]["requestBodies"]["Payload"]["required"] = False
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.post("/payload")
    assert response.status == 200
    assert (await response.json())["body"] is None


async def test_multipart_stream_not_consumed(aiohttp_client, specification):
    async def upload(request):
        assert request["data"]["body"] is request
        assert not request.content.at_eof()
        reader = await request.multipart()
        part = await reader.next()
        return web.Response(body=await part.read())

    client = await make_client(aiohttp_client, specification, upload)
    data = aiohttp.FormData()
    data.add_field("file", b"streamed content", filename="test.txt")
    response = await client.post("/payload", data=data)
    assert response.status == 200
    assert await response.read() == b"streamed content"


@pytest.mark.parametrize("filename", [None, "blob", "metadata.json"])
@pytest.mark.parametrize("content_type", ["application/json", "application/json; charset=utf-8"])
async def test_multipart_json_field_and_json_attachment(
    aiohttp_client, specification, filename, content_type
):
    specification["components"]["schemas"] = {"Metadata": {"type": "object"}}
    specification["components"]["requestBodies"]["Payload"]["content"]["multipart/form-data"] = {
        "schema": {
            "type": "object",
            "properties": {
                "object": {"$ref": "#/components/schemas/Metadata"},
                "attachment": {"type": "string", "format": "binary"},
            },
        }
    }

    async def upload(request):
        hook = PreprocessHook(
            headers=request.headers,
            multipart_reader=await request.multipart(),
            form_fields=request.get(MULTIPART_FORM_FIELDS_KEY),
        )
        files = {}
        async for file in hook.files():
            chunks = [chunk async for chunk in file.read_chunks(chunk_size=8192)]
            files[file.name] = b"".join(chunks).decode()
        return web.json_response({"args": await hook.parsed_args(), "files": files})

    client = await make_client(aiohttp_client, specification, upload)
    data = aiohttp.FormData()
    data.add_field("object", '{"id":"example"}', filename=filename, content_type=content_type)
    # A genuine JSON attachment, even named blob, must still be streamed as a file.
    data.add_field("attachment", b'{"file":true}', filename="blob", content_type="application/json")
    response = await client.post("/payload", data=data)
    assert response.status == 200, await response.text()
    assert await response.json() == {
        "args": {"object": {"id": "example"}, "attachment": "blob"},
        "files": {"attachment": '{"file":true}'},
    }


@pytest.mark.parametrize("docs_path", ["/api/docs", "/api/docs/", "/docs", "/"])
async def test_documentation(aiohttp_client, specification, docs_path):
    client = await make_client(aiohttp_client, specification, echo, docs_path=docs_path)
    path = docs_path.rstrip("/")
    if path:
        response = await client.get(f"{path}?test=1", allow_redirects=False)
        assert response.status == 308
        assert response.headers["Location"] == f"{path}/?test=1"
        response = await client.get(path)
        assert response.status == 200
        assert response.url.path == f"{path}/"
    response = await client.get(f"{path}/")
    assert response.status == 200
    html = await response.text()
    assert "Validation &lt;test&gt;" in html
    assert '<rapi-doc spec-url="./swagger.json"' in html
    assert 'type="module" src="./rapidoc_static/rapidoc-min.js"' in html
    assert 'load-fonts="false"' in html
    assert 'allow-spec-url-load="false"' in html
    assert 'allow-spec-file-load="false"' in html
    response = await client.get(f"{path}/swagger.json")
    assert await response.json() == specification
    response = await client.get(f"{path}/rapidoc_static/rapidoc-min.js")
    assert response.status == 200
    assert response.content_type in {"text/javascript", "application/javascript"}
    assert "rapidoc v10.1.0" in await response.text()


async def test_documentation_disabled(aiohttp_client, specification):
    client = await make_client(aiohttp_client, specification, echo, docs_path=None)
    assert (await client.get("/api/docs/")).status == 404
    assert (await client.post("/payload", json={})).status == 200


async def test_engine_payload_validation(aiohttp_client, monkeypatch, mock_api_app_config):
    from hopeit.server import runtime
    from hopeit.server import web as engine_web
    from hopeit.server.config import AuthType
    from hopeit.server.engine import Server

    config = mock_api_app_config
    config.plugins = []
    config.events = {"mock-app-api-post": config.events["mock-app-api-post"]}
    config.server.auth.enabled = False
    config.server.auth.default_auth_methods = [AuthType.UNSECURED]
    api.clear()
    api.init_auto_api("1.0", "Engine test", "Payload validation")
    api.register_server_config(config.server)
    api.register_apps([config])
    app = web.Application()
    monkeypatch.setattr(engine_web, "web_server", app)
    monkeypatch.setattr(runtime, "server", Server())
    api.enable_swagger(config.server, app)
    await engine_web.server_startup_hook(config.server)
    try:
        await engine_web.app_startup_hook(config, [])
        client = await aiohttp_client(app)
        url = "/api/mock-app-api/test/mock-app-api?arg1=test"
        headers = {"X-Track-Session-Id": "test"}
        # Generated tracking headers have defaults, but must still be supplied.
        response = await client.post(url, json={"value": "ok"})
        assert response.status == 400, await response.text()
        response = await client.post(url, json={"value": "ok"}, headers=headers)
        assert response.status == 200, await response.text()
        assert await response.json() == {"mock-app-api-post": 6}
        response = await client.post(url, json={"value": {"invalid": "object"}}, headers=headers)
        assert response.status == 400, await response.text()
        assert "validation error for RootModel[MockData]" in await response.text()
    finally:
        await runtime.server.stop()
        api.clear()


async def test_engine_multipart_blob(aiohttp_client, monkeypatch, mock_api_app_config):
    from hopeit.server import runtime
    from hopeit.server import web as engine_web
    from hopeit.server.config import AuthType
    from hopeit.server.engine import Server

    config = mock_api_app_config
    config.plugins = []
    config.events = {"mock-app-api-multipart": config.events["mock-app-api-multipart"]}
    config.server.auth.enabled = False
    config.server.auth.default_auth_methods = [AuthType.UNSECURED]
    api.clear()
    api.init_auto_api("1.0", "Multipart test", "JSON blobs")
    api.register_server_config(config.server)
    api.register_apps([config])
    app = web.Application()
    monkeypatch.setattr(engine_web, "web_server", app)
    monkeypatch.setattr(runtime, "server", Server())
    api.enable_swagger(config.server, app)
    await engine_web.server_startup_hook(config.server)
    try:
        await engine_web.app_startup_hook(config, [])
        client = await aiohttp_client(app)
        for json_body, status in [('{"value":"ok"}', 200), ("invalid", 400)]:
            data = aiohttp.FormData()
            data.add_field("field1", "A")
            data.add_field("field2", json_body, filename="blob", content_type="application/json")
            data.add_field("file", b"content", filename="test.txt")
            response = await client.post(
                "/api/mock-app-api/test/mock-app-api-multipart?arg1=test",
                data=data,
                headers={"X-Track-Session-Id": "test"},
            )
            assert response.status == status, await response.text()
            if status == 200:
                assert await response.json() == {
                    "mock-app-api-multipart": len("field1:A field2:ok file:test.txt") + len("test")
                }
    finally:
        await runtime.server.stop()
        api.clear()


@pytest.mark.parametrize("level", ["root", "path", "operation"])
@pytest.mark.parametrize(
    "server", ["http://api.example.com:8020", "https://public.example/gateway", "/gateway"]
)
async def test_documented_servers_do_not_restrict_registered_routes(
    aiohttp_client, specification, level, server
):
    owner = {
        "root": specification,
        "path": specification["paths"]["/items/{item}"],
        "operation": specification["paths"]["/items/{item}"]["get"],
    }[level]
    owner["servers"] = [{"url": server}]
    original = deepcopy(specification)
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.get(
        "/items/7?count=2",
        headers={"Host": "api.example.com:8020", "X-Test": "ok", "Cookie": "session=ok"},
    )
    assert response.status == 200, await response.text()
    assert (await response.json())["item"] == 7
    docs = await client.get("/api/docs/swagger.json")
    assert await docs.json() == original


@pytest.mark.parametrize(
    "location,name,default",
    [
        ("query", "count", 1),
        ("header", "X-Test", "test.caller"),
        ("cookie", "session", "test.session"),
    ],
)
async def test_required_parameter_defaults_do_not_supply_missing_input(
    aiohttp_client, specification, location, name, default
):
    parameters = specification["paths"]["/items/{item}"]["get"]["parameters"]
    next(p for p in parameters if p["name"] == name)["schema"]["default"] = default
    client = await make_client(aiohttp_client, specification, echo)
    headers = {"X-Test": "ok", "Cookie": "session=ok"}
    if location == "header":
        del headers["X-Test"]
    elif location == "cookie":
        del headers["Cookie"]
    response = await client.get(
        "/items/7" + ("" if location == "query" else "?count=2"), headers=headers
    )
    assert response.status == 400, await response.text()


@pytest.mark.parametrize("value,status", [("", 200), ("a", 200)])
async def test_empty_query_strings(aiohttp_client, specification, value, status):
    specification["paths"]["/items/{item}"]["get"]["parameters"] = [
        {"name": "text", "in": "query", "required": True, "schema": {"type": "string"}},
    ]
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.get("/items/7", params={"text": value})
    assert response.status == status, await response.text()
    assert (await response.json())["text"] == value
    assert (await client.get("/items/7")).status == 400


async def test_empty_query_string_still_validates_constraints(aiohttp_client, specification):
    specification["paths"]["/items/{item}"]["get"]["parameters"] = [
        {"name": "text", "in": "query", "schema": {"type": "string", "minLength": 1}},
    ]
    client = await make_client(aiohttp_client, specification, echo)
    assert (await client.get("/items/7?text=")).status == 400


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        ("false", False),
        ("TRUE", None),
        ("FALSE", None),
        ("1", None),
        ("0", None),
        ("yes", None),
        ("no", None),
        ("", None),
    ],
)
@pytest.mark.parametrize("array", [False, True])
async def test_boolean_wire_values(aiohttp_client, specification, value, expected, array):
    schema = {"type": "boolean"}
    if array:
        schema = {"type": "array", "items": schema}
    specification["paths"]["/items/{item}"]["get"]["parameters"] = [
        {"name": "enabled", "in": "query", "schema": schema},
    ]
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.get("/items/7", params={"enabled": value})
    assert response.status == (400 if expected is None else 200), await response.text()
    if expected is not None:
        assert (await response.json())["enabled"] == ([expected] if array else expected)


async def test_parameter_refs_overrides_and_optional_defaults(aiohttp_client, specification):
    specification["components"]["schemas"] = {"Count": {"type": "integer", "default": 2}}
    specification["components"]["parameters"] = {
        "Count": {
            "name": "count",
            "in": "query",
            "required": True,
            "schema": {"$ref": "#/components/schemas/Count"},
        }
    }
    path = specification["paths"]["/items/{item}"]
    path["parameters"].append({"$ref": "#/components/parameters/Count"})
    path["get"]["parameters"] = []
    client = await make_client(aiohttp_client, specification, echo)
    assert (await client.get("/items/7")).status == 400
    response = await client.get("/items/7?count=3")
    assert response.status == 200
    assert (await response.json())["count"] == 3
    # An operation may override a required path-item parameter with an optional one.
    path["get"]["parameters"] = [
        {"name": "count", "in": "query", "schema": {"$ref": "#/components/schemas/Count"}}
    ]
    client = await make_client(aiohttp_client, specification, echo)
    response = await client.get("/items/7")
    assert response.status == 200
    assert (await response.json())["count"] == 2
