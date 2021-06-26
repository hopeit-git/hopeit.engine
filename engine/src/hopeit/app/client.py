"""
Client to invoke events in configured connected Apps
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import partial
import random
from typing import Any, Dict, List, Optional, Tuple, Type

import aiohttp
from stringcase import spinalcase  # type: ignore

from hopeit.app.context import EventContext
from hopeit.app.config import AppConfig, EventConnection, EventConnectionType
from hopeit.app.errors import Unauthorized
from hopeit.dataobjects import EventPayload, dataobject
from hopeit.dataobjects.jsonify import Json
from hopeit.toolkit import auth
from hopeit.server.logger import engine_extra_logger

logger, extra = engine_extra_logger()

_registered_clients = {}


@dataobject
@dataclass
class AppsClientEnv:
    circuit_breaker_open_failures: int = 10
    circuit_breaker_failure_reset_seconds: int = 120
    circuit_breaker_open_seconds: int = 60
    retries: int = 1
    retry_backoff_ms: int = 10
    ssl: bool = True
    max_connections: int = 100
    max_connections_per_host: int = 0
    dns_cache_ttl: int = 10


@dataclass
class CircuitBreakLoadBalancer:
    hosts: List[str]
    host_index: int = 0
    cb_failures: List[int] = field(default_factory=list)
    cb_failure_reset_ttl: List[int] = field(default_factory=list)
    cb_open_ttl: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.cb_failures = [0] * len(self.hosts)
        self.cb_reset_ttl = [0] * len(self.hosts)
        self.cb_open_ttl = [0] * len(self.hosts)

    def host(self, i: int) -> str:
        return self.hosts[i]

    def next_host(self, now_ts: int) -> Tuple[int, bool]:
        i = self.host_index
        self.host_index = (self.host_index + 1) % len(self.hosts)
        return i, self.cb_open_ttl[i] < now_ts

    def randomize_next_host(self):
        self.host_index = random.randint(0, len(self.hosts) - 1)

    def success(self, host_index: int):
        self.cb_open_ttl[host_index] = 0
        self.cb_failures[host_index] = 0

    def failure(self, host_index: int, now_ts: int,
                circuit_breaker_open_failures: int,
                circuit_breaker_failure_reset_seconds: int, 
                circuit_breaker_open_seconds: int):
        if circuit_breaker_open_failures == 0:  # Circuit breaker disabled
            return
        failures = (
            self.cb_failures[host_index]
            if now_ts < self.cb_reset_ttl[host_index]
            else 0
        )
        self.cb_failures[host_index] = min(
            circuit_breaker_open_failures, failures + 1
        )
        self.cb_reset_ttl[host_index] = now_ts + circuit_breaker_failure_reset_seconds
        if self.cb_failures[host_index] >= circuit_breaker_open_failures:
            self.cb_open_ttl[host_index] = now_ts + circuit_breaker_open_seconds


class ClientLoadBalancerException(Exception):
    """Client load balancer errors"""


class AppsClientException(Exception):
    """AppsClient error wrapper"""


class ServerException(Exception):
    """Wrapper for 5xx responses"""


@dataclass
class AppConnectionState:
    app_connection: str
    load_balancer: CircuitBreakLoadBalancer
    events: Dict[str, Dict[str, EventConnection]] = field(default_factory=partial(defaultdict, dict))


class AppsClient:
    """
    AppsClient: Manages connections and invokations to external App events.
    """
    def __init__(self, app_config: AppConfig):
        self.app_key = app_config.app_key()
        self.env = Json.from_obj(app_config.env.get('apps_client', {}), AppsClientEnv)
        self.app_connections = app_config.app_connections
        self.event_connections = {
            event_name: event_info.connections
            for event_name, event_info in app_config.events.items()
        }
        self.conn_info: Dict[str, AppConnectionState] = {}
        self.session: Optional[Any] = None
        self.token: Optional[str] = None
        self.token_expire: int = 0

    async def start(self):
        logger.info(__name__, "Initializing client...", extra=extra(app=self.app_key))
        self._register_event_connections()
        self._create_session()
        self._ensure_token(self._now_ts())
        logger.info(__name__, "Client ready.", extra=extra(app=self.app_key))
        return self

    async def stop(self):
        logger.info(__name__, "Stopping client...", extra=extra(app=self.app_key))
        try:
            await self.session.close()
        except Exception as e:
            logger.error(__name__, str(e))
        finally:
            await asyncio.sleep(1.0)
            self.session = None
            self.token = None
            self.token_expire = 0.0
            logger.info(__name__, "Client stopped.", extra=extra(app=self.app_key))


    async def call(self, app_connection: str, event_name: str,
                   *, datatype: Type[EventPayload], payload: Optional[EventPayload],
                   context: EventContext, **kwargs) -> EventPayload:
        """
        Invokes event on external app linked in config `app_connections` section.
        Target event must also be configured in event `client` section

        :param: app_connection, str: name of configured app_connection to connect to
        :param: event_name, str: target event name to inoke, configured in events section
        :datatype: Type[EventPayloadType]: expected return type
        :payload: optional payload to send when calling external event
        :context: EventContext of current application
        **kwargs: any other argument to be sent as query args when calling event

        :return: datatype, returned data from invoked event, converted to datatype
        """
        now_ts = self._now_ts()
        conn = self.conn_info[app_connection]
        event_info = conn.events[context.event_name][event_name]
        token = self._ensure_token(now_ts)
        headers = self._request_headers(context, token)

        for retry_count in range(self.env.retries + 1):
            host_index = self._next_available_host(conn, now_ts, context)
            host = conn.load_balancer.host(host_index)
            route = f"{host}/{event_info.route.lstrip('/')}"
            result = None
            logger.info(
                context, f"{'Calling' if retry_count == 0 else 'Retrying call to'} external app...",
                extra=extra(
                    app_connection=app_connection, event=event_name, route=route, retry_count=retry_count
                )
            )

            try:
                if event_info.type == EventConnectionType.GET:
                    async with self.session.get(route, headers=headers, **kwargs) as response:
                        result = await self._parse_response(response, context, datatype)

                if event_info.type == EventConnectionType.POST:
                    async with self.session.post(route, headers=headers, 
                                                body=Json.to_obj(payload), **kwargs) as response:
                        result = await self._parse_response(response, context, datatype)

            except (ServerException, IOError) as e:
                conn.load_balancer.failure(
                    host_index, now_ts, 
                    self.env.circuit_breaker_open_failures,
                    self.env.circuit_breaker_failure_reset_seconds,
                    self.env.circuit_breaker_open_seconds
                )
                if retry_count == self.env.retries:
                    raise AppsClientException(f"Server or IO Error: " + str(e) + 
                        f" ({retry_count} retries)" if retry_count else ""
                    ) from e
                logger.error(context, e)
                await asyncio.sleep(0.001 * self.env.retry_backoff_ms)
                continue

            conn.load_balancer.success(host_index)
            return result

    def _now_ts(self) -> int:
        return int(datetime.now(tz=timezone.utc).timestamp())

    def _create_session(self):
        logger.info(__name__, "Creating client session...", extra=extra(app=self.app_key))
        connector = aiohttp.TCPConnector(
            ssl=self.env.ssl,
            limit=self.env.max_connections,
            limit_per_host=self.env.max_connections_per_host,
            use_dns_cache=self.env.dns_cache_ttl > 0,
            ttl_dns_cache=self.env.dns_cache_ttl
        )
        self.session = aiohttp.ClientSession(connector=connector)

    def _ensure_token(self, now_ts: int):
        if now_ts >= self.token_expire:
            logger.info(__name__, "Renewing client access token...", extra=extra(app=self.app_key))
            self.token = self._create_access_token(now_ts, timeout=60, renew=50)
            self.token_expire = now_ts + 50
        return self.token

    def _create_access_token(self, now_ts: int, timeout: int, renew: int) -> str:
        """
        Returns a new access token encoding `info` and expiring in `access_token_expiration` seconds
        """
        auth_payload = {
            "iat": now_ts,
            "exp": now_ts + timeout
        }
        return auth.new_token(self.app_key, auth_payload)

    def _register_event_connections(self):
        logger.info(__name__, "Registering client connections...", extra=extra(app=self.app_key))
        for app_connection, info in self.app_connections.items():
            lb = CircuitBreakLoadBalancer(
                hosts=info.hosts.split(',')
            )
            self.conn_info[app_connection] = AppConnectionState(
                app_connection=app_connection,
                load_balancer=lb
            )
        for event_name, connections in self.event_connections.items():
            for info in connections:
                conn_info = self.conn_info[info.app_connection]
                conn_info.events[event_name][info.event] = info

    def _request_headers(self, context: EventContext, token: str):
        return {
            **{
                f"x-{spinalcase(k)}": str(v)
                for k, v in context.track_ids.items()
            },
            "x-track-client-app-key": context.app_key,
            "x-track-client-event-name": context.event_name,
            "authorization": f"Bearer {token}"
        }

    async def _parse_response(self, response, context: EventContext,
                              datatype: Type[EventPayload]) -> EventPayload:
        """
        Parses http response from external App, catching Unathorized errors
        and converting the result to the desired datatype
        """
        if response.status == 200:
            data = await response.json()
            if isinstance(data, list):
                return Json.from_obj(data, list, item_datatype=datatype)  # type: ignore
            if isinstance(data, dict):
                return Json.from_obj(data, dict, item_datatype=datatype)  # type: ignore
            return Json.from_obj(data, datatype)
        if response.status == 401:
            raise Unauthorized(context.app_key)
        if response.status >= 500:
            raise ServerException(await response.text())
        raise RuntimeError(await response.text())

    def _next_available_host(self, conn: AppConnectionState, now_ts: int, context: EventContext) -> int:
        for _ in range(len(conn.load_balancer.hosts)):
            host_index, ok = conn.load_balancer.next_host(now_ts)
            if not ok:
                logger.warning(context, "Circuit breaker open for host", extra=extra(
                    host=conn.load_balancer.host(host_index)
                ))
            else:
                return host_index
        conn.load_balancer.randomize_next_host()
        raise ClientLoadBalancerException("No hosts available.")


async def register_apps_client(app_config: AppConfig):
    client = await AppsClient(app_config).start()
    _registered_clients[app_config.app_key()] = client


def app_client(context: EventContext) -> AppsClient:
    return _registered_clients[context.app_key]
