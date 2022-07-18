from typing import Dict, List, Union
from collections import defaultdict
import asyncio

from hopeit.app.config import AppConfig
from hopeit.server import engine
from hopeit.server.version import APPS_ROUTE_VERSION
from hopeit.dataobjects import dataobject, dataclass
from hopeit.dataobjects.payload import Payload


@dataobject
@dataclass
class MockResponseData:
    value: str
    param: str
    host: str
    log: Dict[str, int]


@dataobject
@dataclass
class MockPayloadData:
    value: str


class MockAppEngine:
    def __init__(self, app_config: AppConfig):
        self.app_config = app_config


class MockServer:
    def __init__(self, *app_config: AppConfig):
        self.app_engines = {
            cfg.app_key(): MockAppEngine(cfg)
            for cfg in app_config
        }


class MockResponse():
    def __init__(self, status: int, response: Union[MockResponseData, str], content_type: str = "application/json"):
        self.status = status
        self.response = response
        self.content_type = content_type

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def json(self):
        return Payload.to_obj(self.response)

    async def text(self):
        return str(self.response)


class MockResponseList():
    def __init__(self, status: int, items: List[MockResponseData], content_type: str = "application/json"):
        self.status = status
        self.items = items
        self.content_type = content_type

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def json(self):
        return Payload.to_obj(self.items)

    async def text(self):
        return f"status {self.status}"


class MockClientSession():
    lock = asyncio.Lock()
    session_open = False
    responses: Dict[str, str] = {}
    headers: Dict[str, str] = {}
    failure: Dict[str, int] = {}
    alternate: Dict[str, int] = {}
    call_log: Dict[str, int] = defaultdict(int)

    @classmethod
    def setup(cls, responses: Dict[str, str], headers: Dict[str, str]):
        cls.responses = responses
        cls.headers = headers
        cls.failure = {
            cls._host(url): 0 for url in responses.keys()
        }
        cls.call_log = defaultdict(int)
        cls.session_open = False
        return cls

    @classmethod
    def set_failure(cls, host: str, failure: int):
        cls.failure[cls._host(host)] = failure
        return cls

    @classmethod
    def set_alternate_response(cls, host: str, status: int):
        cls.alternate[cls._host(host)] = status
        return cls

    def __init__(self, *args, **kwargs):
        type(self).session_open = True

    async def close(self):
        type(self).session_open = False

    async def __aenter__(self):
        type(self).session_open = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        type(self).session_open = False
        return None

    @staticmethod
    def _host(url: str):
        return '/'.join(url.split('/')[0:3])

    def _check_headers(self, headers: dict):
        for k, v in self.headers.items():
            assert headers[k] == v

    def get(self, url: str, headers: dict, params: dict) -> MockResponse:
        self._check_headers(headers)
        host = self._host(url)
        self.call_log[host] += 1
        if self.failure.get(host):
            return MockResponse(
                self.failure.get(host, 0), "Mock server error"
            )
        if self.alternate.get(host):
            status = self.alternate.get(host)
            assert status
            return MockResponse(status, MockResponseData(
                value=self.responses[url],
                param=str(params.get("test_param", "")),
                host=host,
                log=dict(self.call_log)
            ))
        if url in self.responses:
            return MockResponse(200, MockResponseData(
                value=self.responses[url],
                param=str(params.get("test_param", "")),
                host=host,
                log=dict(self.call_log)
            ))
        raise IOError("Test error")

    def post(self, url: str, data: str, headers: dict,
             params: dict) -> Union[MockResponseList, MockResponse]:
        self._check_headers(headers)
        host = self._host(url)
        self.call_log[host] += 1
        if self.failure.get(host):
            return MockResponse(
                self.failure.get(host, 0), "Mock server error"
            )
        if self.alternate.get(host):
            status = self.alternate.get(host)
            assert status
            payload = Payload.from_json(data, MockPayloadData)
            return MockResponseList(status, items=[MockResponseData(
                value=f"{payload.value} {self.responses[url]}",
                param=str(params.get("test_param", "")),
                host=host,
                log=self.call_log
            )])
        if url in self.responses:
            payload = Payload.from_json(data, MockPayloadData)
            return MockResponseList(200, items=[MockResponseData(
                value=f"{payload.value} {self.responses[url]}",
                param=str(params.get("test_param", "")),
                host=host,
                log=self.call_log
            )])
        raise IOError("Test error")


async def init_mock_client_app(module, monkeypatch, mock_auth, app_config, event_name, response):
    monkeypatch.setattr(engine, "auth", mock_auth)
    monkeypatch.setattr(module, "auth", mock_auth)
    url_pattern = "{}/api/test-app/{}/{}"
    url1 = url_pattern.format("http://test-host1", APPS_ROUTE_VERSION, event_name)
    url2 = url_pattern.format("http://test-host2", APPS_ROUTE_VERSION, event_name)
    monkeypatch.setattr(module.aiohttp, 'ClientSession', MockClientSession.setup(
        responses={
            url1: response,
            url2: response
        },
        headers={
            "authorization": "Bearer test-token"
        }
    ))
    await engine.AppEngine(app_config=app_config, plugins=[], enabled_groups=[], streams_enabled=False).start()


async def init_mock_client_app_plugin(module, monkeypatch, mock_auth, app_config, plugin_name, event_name, response):
    monkeypatch.setattr(engine, "auth", mock_auth)
    monkeypatch.setattr(module, "auth", mock_auth)
    url_pattern = "{}/api/test-app/{}/{}/{}/{}"
    url1 = url_pattern.format("http://test-host1", APPS_ROUTE_VERSION, plugin_name, APPS_ROUTE_VERSION, event_name)
    url2 = url_pattern.format("http://test-host2", APPS_ROUTE_VERSION, plugin_name, APPS_ROUTE_VERSION, event_name)
    monkeypatch.setattr(module.aiohttp, 'ClientSession', MockClientSession.setup(
        responses={
            url1: response,
            url2: response
        },
        headers={
            "authorization": "Basic user:pass"
        }

    ))
    await engine.AppEngine(app_config=app_config, plugins=[], enabled_groups=[], streams_enabled=False).start()
