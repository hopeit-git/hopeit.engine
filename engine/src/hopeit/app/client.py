"""
Client to invoke events in configured connected Apps
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple, Type, Union

import aiohttp
from stringcase import spinalcase  # type: ignore

from hopeit.app.context import EventContext
from hopeit.app.config import AppConfig, EventConnectionType
from hopeit.app.errors import Unauthorized
from hopeit.dataobjects import EventPayload
from hopeit.dataobjects.jsonify import Json
from hopeit.toolkit.auth import new_token

_registered_clients = {}


class AppsClient:
    """
    AppsClient: Manages connections and invokations to external App events.
    """
    def __init__(self, app_config: AppConfig):
        self.app_connections = app_config.app_connections
        self.event_connections = {
            event_name: event_info.connections
            for event_name, event_info in app_config.events.items()
        }
        self.conn_info: Dict[str, Dict[Tuple[str, str], Tuple[str, str, str]]] = {}

    async def start(self):
        for event_name, connections in self.event_connections.items():
            for info in connections:
                app_connection = self.app_connections[info.app_connection]
                self.conn_info[event_name] = {
                    (info.app_connection, info.event): (
                        info.type, info.route, app_connection.hosts.split(',')
                    )
                }
        return self

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
        call_type, route, hosts = self.conn_info[context.event_name][(app_connection, event_name)]

        async with aiohttp.ClientSession() as client:

            token = access_token(
                context.auth_info.get('payload'), context, now=datetime.now(tz=timezone.utc), timeout=10, renew=10
            )

            if call_type == EventConnectionType.GET:
                async with client.get(
                    f"{hosts[0]}/{route.lstrip('/')}",
                    headers=self._request_headers(context, token),
                    **kwargs
                ) as response:
                    return await self._parse_response(response, context, datatype)

            if call_type == EventConnectionType.POST:
                async with client.post(
                    f"{hosts[0]}/{route.lstrip('/')}",
                    body=Json.to_obj(payload),
                    headers=self._request_headers(context, token),
                    **kwargs
                ) as response:
                    return await self._parse_response(response, context, datatype)

            raise NotImplementedError()


async def register_apps_client(app_config: AppConfig):
    client = await AppsClient(app_config).start()
    _registered_clients[app_config.app_key()] = client


def app_client(context: EventContext) -> AppsClient:
    return _registered_clients[context.app_key]


def access_token(info: Union[dict, Any], context: EventContext, now: datetime, timeout: int, renew: int):
    """
    Returns a new access token encoding `info` and expiring in `access_token_expiration` seconds
    """
    auth_payload = {
        **(context.auth_info if isinstance(context.auth_info, dict) else {}),
        "iat": now,
        "exp": now + timedelta(seconds=timeout),
        "renew": renew
    }
    return new_token(context.app_key, auth_payload)
