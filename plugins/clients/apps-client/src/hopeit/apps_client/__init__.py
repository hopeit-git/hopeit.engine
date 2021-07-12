"""
Client to invoke events in configured connected Apps
"""
from contextlib import AbstractAsyncContextManager
from typing import Any, Dict, List, Optional, Tuple, Type
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import partial
import random

import aiohttp
from stringcase import spinalcase  # type: ignore

from hopeit.app.client import AppConnectionNotFound, Client, ClientException
from hopeit.app.context import EventContext
from hopeit.app.config import AppConfig, AppDescriptor, EventConnection, EventConnectionType
from hopeit.app.errors import Unauthorized
from hopeit.dataobjects import EventPayload, EventPayloadType, dataobject
from hopeit.dataobjects.payload import Payload
from hopeit.toolkit import auth
from hopeit.server.logger import engine_extra_logger
from hopeit.server.api import app_route_name

logger, extra = engine_extra_logger()


@dataobject
@dataclass
class AppsClientSettings:
    """
    AppsClient configuration

    :field: connection_str, str: comma-separated list of `http://host:port` urls
    # TODO add fields doc
    """
    connection_str: str
    circuit_breaker_open_failures: int = 10
    circuit_breaker_failure_reset_seconds: int = 120
    circuit_breaker_open_seconds: int = 60
    retries: int = 1
    retry_backoff_ms: int = 10
    ssl: bool = True
    max_connections: int = 100
    max_connections_per_host: int = 0
    dns_cache_ttl: int = 10
    routes_override: Dict[str, str] = field(default_factory=dict)


@dataclass
class CircuitBreakLoadBalancer:
    """
    Simple round robin load-balancer with a circuit breaker.

    Load balancer will pick the next host in the available hosts list,
    and will keep track of failures/success calls to each host.
    If number of failures `cb_failures` in a `cb_failure_reset` timeframe is exceeded,
    circuit breaker for the failing host will be open and not returned in subsequent calls
    to `next_available_hosts` until `cb_open_ttl` is exhausted.

    The best behaviour is achieved when `cb_failure_reset` is slightly bigger than `cb_open_ttl`.
    This way, when circuit breaker closes after open_ttl timesout, failure count will not be reset
    to zero, which will lead to immeadiatelly open the circuit breaker in the next call.

    After one sucessfull call to a host when `cb_open_ttl` expired, failure counter will be reset.
    """
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
        """
        Gets notified of failures and opens circuit breaker if necessary
        """
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


class ClientLoadBalancerException(ClientException):
    """Client load balancer errors"""


class AppsClientException(ClientException):
    """AppsClient error wrapper"""


class ServerException(ClientException):
    """Wrapper for 5xx responses from services when invoked using client"""


@dataclass
class AppConnectionState:
    app_connection: str
    load_balancer: CircuitBreakLoadBalancer
    events: Dict[str, Dict[str, EventConnection]] = field(
        default_factory=partial(defaultdict, dict)  # type: ignore
    )


class AppsClient(Client):
    """
    AppsClient: Manages connections and calls to external App events.
    """
    def __init__(self, app_config: AppConfig, app_connection: str):
        self.app_key = app_config.app_key()
        self.app_conn_key = app_connection
        self.app_connection = app_config.app_connections[app_connection]
        settings_key = self.app_connection.settings or app_connection
        self.settings = Payload.from_obj(app_config.settings.get(settings_key, {}), AppsClientSettings)
        self.event_connections = {
            event_name: {
                conn.event: conn
                for conn in event_info.connections
                if conn.app_connection == app_connection
            }
            for event_name, event_info in app_config.events.items()
        }
        self.routes = {
            conn.event: self._get_route(conn.event)
            for event_info in app_config.events.values()
            for conn in event_info.connections
            if conn.app_connection == app_connection
        }
        self.conn_state: Optional[AppConnectionState] = None
        self.session: Optional[Any] = None
        self.token: Optional[str] = None
        self.token_expire: int = 0

    def _get_route(self, event_name: str):
        app_descriptor = AppDescriptor(
            name=self.app_connection.name,
            version=self.app_connection.version
        )
        return app_route_name(
            app_descriptor, event_name=event_name,
            override_route_name=self.settings.routes_override.get(event_name)
        )

    async def start(self):
        """
        Starts client instance and creates an aiohttp.ClientSession.
        Initializes an auth token.
        """
        logger.info(__name__, "Initializing client...", extra=extra(
            app=self.app_key, app_connection=self.app_conn_key
        ))
        self._register_event_connections()
        self._create_session()
        self._ensure_token(self._now_ts())
        logger.info(__name__, "Client ready.", extra=extra(
            app=self.app_key, app_connection=self.app_conn_key
        ))
        return self

    async def stop(self):
        """
        Release session connections
        """
        logger.info(__name__, "Stopping client...", extra=extra(
            app=self.app_key, app_connection=self.app_conn_key
        ))
        try:
            await self.session.close()
        except Exception as e:  # pylint: disable=broad-except
            logger.error(__name__, str(e))
        finally:
            await asyncio.sleep(1.0)
            self.session = None
            self.token = None
            self.token_expire = 0.0
            logger.info(__name__, "Client stopped.", extra=extra(
                app=self.app_key, app_connection=self.app_conn_key
            ))

    async def call(self, event_name: str,
                   *, datatype: Type[EventPayloadType], payload: Optional[EventPayload],
                   context: EventContext, **kwargs) -> List[EventPayloadType]:
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
        if self.conn_state is None or self.session is None:
            raise RuntimeError("AppsClient not started: `client.start()` must be called from engine.")
        now_ts = self._now_ts()
        event_info = self._get_event_connection(context, event_name)
        token = self._ensure_token(now_ts)
        headers = self._request_headers(context, token)

        for retry_count in range(self.settings.retries + 1):
            host_index = self._next_available_host(self.conn_state, now_ts, context)
            host = self.conn_state.load_balancer.host(host_index)
            route = self.routes[event_name]
            url = host + route
            logger.info(
                context, f"{'Calling' if retry_count == 0 else 'Retrying call to'} external app...",
                extra=extra(
                    app_connection=self.app_conn_key, event=event_name, url=url, retry_count=retry_count
                )
            )

            try:
                if event_info.type == EventConnectionType.GET:
                    request_func = self.session.get(url, headers=headers, params=kwargs)
                    return await self._request(
                        request_func, context, datatype, event_name, host_index
                    )

                if event_info.type == EventConnectionType.POST:
                    request_func = self.session.post(
                        url, headers=headers, data=Payload.to_json(payload), params=kwargs
                    )
                    return await self._request(
                        request_func, context, datatype, event_name, host_index
                    )

                raise NotImplementedError(f"Event type {event_info.type.value} not supported")

            except (ServerException, IOError) as e:
                self.conn_state.load_balancer.failure(
                    host_index, now_ts,
                    self.settings.circuit_breaker_open_failures,
                    self.settings.circuit_breaker_failure_reset_seconds,
                    self.settings.circuit_breaker_open_seconds
                )
                if retry_count == self.settings.retries:
                    raise AppsClientException(
                        f"Server or IO Error: {e} ({retry_count} retries)"
                    ) from e
                logger.error(context, e)
                await asyncio.sleep(0.001 * self.settings.retry_backoff_ms)

        raise RuntimeError("Unexpected missing result after retry loop")

    def _now_ts(self) -> int:
        return int(datetime.now(tz=timezone.utc).timestamp())

    def _get_event_connection(self, context: EventContext, event_name: str):
        try:
            return self.event_connections[context.event_name][event_name]
        except KeyError:
            raise AppConnectionNotFound(  # pylint: disable=raise-missing-from
                f"Event {event_name} not found in event connections for {context.event_name}"
            )

    def _create_session(self):
        """
        Creates aiohttp ClientSession hold by the client
        """
        logger.info(__name__, "Creating client session...", extra=extra(
            app=self.app_key, app_connection=self.app_conn_key
        ))
        connector = aiohttp.TCPConnector(
            ssl=self.settings.ssl,
            limit=self.settings.max_connections,
            limit_per_host=self.settings.max_connections_per_host,
            use_dns_cache=self.settings.dns_cache_ttl > 0,
            ttl_dns_cache=self.settings.dns_cache_ttl
        )
        self.session = aiohttp.ClientSession(connector=connector)

    def _ensure_token(self, now_ts: int):
        if now_ts >= self.token_expire:
            logger.info(__name__, "Renewing client access token...", extra=extra(
                app=self.app_key, app_connection=self.app_conn_key
            ))
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
        logger.info(__name__, "Registering client connections...", extra=extra(
            app=self.app_key, app_connection=self.app_conn_key
        ))
        lb = CircuitBreakLoadBalancer(
            hosts=self.settings.connection_str.split(',')
        )
        self.conn_state = AppConnectionState(
            app_connection=self.app_conn_key,
            load_balancer=lb
        )

    def _request_headers(self, context: EventContext, token: str):
        return {
            **{
                f"x-{spinalcase(k)}": str(v)
                for k, v in context.track_ids.items()
            },
            "x-track-client-app-key": context.app_key,
            "x-track-client-event-name": context.event_name,
            "authorization": f"Bearer {token}",
            "content-type": "application/json"
        }

    async def _parse_response(self, response, context: EventContext,
                              datatype: Type[EventPayloadType],
                              target_event_name: str) -> List[EventPayloadType]:
        """
        Parses http response from external App, catching Unathorized errors
        and converting the result to the desired datatype
        """
        if response.status == 200:
            data = await response.json()
            if isinstance(data, list):
                return Payload.from_obj(data, list, item_datatype=datatype)  # type: ignore
            return [Payload.from_obj(data, datatype, key=target_event_name)]
        if response.status == 401:
            raise Unauthorized(context.app_key)
        if response.status >= 500:
            raise ServerException(await response.text())
        raise RuntimeError(await response.text())

    async def _request(self, request_func: AbstractAsyncContextManager, context: EventContext,
                       datatype: Type[EventPayloadType],
                       target_event_name: str,
                       host_index: int) -> List[EventPayloadType]:
        async with request_func as response:
            result = await self._parse_response(
                response, context, datatype, target_event_name
            )
            self.conn_state.load_balancer.success(host_index)  # type: ignore
            return result

    def _next_available_host(self, conn: AppConnectionState, now_ts: int, context: EventContext) -> int:
        """
        Returns next host to be invoked, from the configured hosts lists and discarding
        hosts marked as not available from the load balancer (i.e. open circuit breaker)
        """
        for _ in range(len(conn.load_balancer.hosts)):
            host_index, ok = conn.load_balancer.next_host(now_ts)
            if not ok:
                logger.warning(context, "Circuit breaker open for host", extra=extra(
                    app_connection=self.app_conn_key, host=conn.load_balancer.host(host_index)
                ))
            else:
                return host_index
        conn.load_balancer.randomize_next_host()
        raise ClientLoadBalancerException("No hosts available.")
