"""
Client to invoke events in configured connected Apps
"""
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import aiohttp
from stringcase import spinalcase  # type: ignore

from hopeit.app.context import EventContext
from hopeit.app.config import AppConfig, EventConnection, EventConnectionType
from hopeit.app.errors import Unauthorized
from hopeit.dataobjects import EventPayload
from hopeit.dataobjects.jsonify import Json
from hopeit.toolkit import auth
from hopeit.server.logger import engine_extra_logger

logger, extra = engine_extra_logger()

_registered_clients = {}


@dataclass
class AppConnectionInfo:
    app_connection: str
    hosts: List[str]
    host_index: int = 0
    events: Dict[str, Dict[str, EventConnection]] = field(default_factory=partial(defaultdict, dict))

    def next_host(self) -> str:
        host = self.hosts[self.host_index]
        self.host_index = (self.host_index + 1) % len(self.hosts)
        return host



class AppsClient:
    """
    AppsClient: Manages connections and invokations to external App events.
    """
    def __init__(self, app_config: AppConfig):
        self.app_key = app_config.app_key()
        self.app_connections = app_config.app_connections
        self.event_connections = {
            event_name: event_info.connections
            for event_name, event_info in app_config.events.items()
        }
        self.conn_info: Dict[str, AppConnectionInfo] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.token: Optional[str] = None
        self.token_expire: int = 0

    async def start(self):
        logger.info(__name__, "Initializing client...", extra=extra(app=self.app_key))
        self._register_event_connections()
        self._create_session()
        self._ensure_token()
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
        conn_info = self.conn_info[app_connection]
        event_info = conn_info.events[context.event_name][event_name]
        token = self._ensure_token()
        host = conn_info.next_host()
        route = f"{host}/{event_info.route.lstrip('/')}"
        headers =self._request_headers(context, token)

        logger.info(context, "Calling external app...", extra=extra(
            app_connection=app_connection, event=event_name, route=route
        ))
        if event_info.type == EventConnectionType.GET:
            async with self.session.get(route, headers=headers, **kwargs) as response:
                return await self._parse_response(response, context, datatype)

        if event_info.type == EventConnectionType.POST:
            async with self.session.post(route, headers=headers, 
                                         body=Json.to_obj(payload), **kwargs) as response:
                return await self._parse_response(response, context, datatype)

        raise NotImplementedError()

    def _create_session(self):
        logger.info(__name__, "Creating client session...", extra=extra(app=self.app_key))
        self.session = aiohttp.ClientSession()

    def _ensure_token(self):
        now = int(datetime.now(tz=timezone.utc).timestamp())
        if now >= self.token_expire:
            logger.info(__name__, "Renewing client access token...", extra=extra(app=self.app_key))
            self.token = self._create_access_token(now, timeout=60, renew=50)
            self.token_expire = now + 50
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
            self.conn_info[app_connection] = AppConnectionInfo(
                app_connection=app_connection,
                hosts=info.hosts.split(',')
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

    async def _parse_response(self, response, context: EventContext, datatype: Type[EventPayload]):
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
        raise RuntimeError(await response.text())


async def register_apps_client(app_config: AppConfig):
    client = await AppsClient(app_config).start()
    _registered_clients[app_config.app_key()] = client


def app_client(context: EventContext) -> AppsClient:
    return _registered_clients[context.app_key]
