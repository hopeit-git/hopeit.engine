"""
Context information and handling
"""
from pathlib import Path
from typing import Dict, Optional, Any, Tuple, Union, List
from datetime import datetime, timezone

from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, Env, EventType

__all__ = ['EventContext',
           'PostprocessHook']


class EventContext:
    """
    EventContext information, shared between engine components
    when an event is executed. Instances of this class are
    created automatically by the engine on every request.

    Instantiated objects contain static information during app lifecycle:
    :param app_key: app key string of the engine app running
    :param app: AppDescriptor of the engine app running
    :param env: dict of env configuration and dynamic information per event execution:
    :param event_name: str
    :param event_info: EventDescriptor of the event executed
    :param track_ids: dict of keys and id values to be tracked
    """
    def __init__(self, *,
                 app_config: AppConfig,
                 plugin_config: AppConfig,
                 event_name: str,
                 track_ids: Dict[str, str],
                 auth_info: Dict[str, Any]):
        self.app_key: str = app_config.app_key()
        self.app: AppDescriptor = app_config.app
        self.env: Env = {**plugin_config.env, **app_config.env}
        self.event_name = event_name
        base_event = event_name.split('$')[0]
        self.event_info: EventDescriptor = plugin_config.events[base_event]
        self.creation_ts: datetime = datetime.now().astimezone(tz=timezone.utc)
        self.auth_info = auth_info
        track_fields = [
            'track.operation_id',
            *app_config.engine.track_headers,
            *(self.event_info.config.logging.stream_fields
              if self.event_info.type == EventType.STREAM
              else [])
        ]
        self.track_ids = {k: track_ids.get(k) or '' for k in track_fields}


class PostprocessHook:
    """
    Post process hook that keeps additional changes to add to response on
    postprocess(...) event methods.

    Useful to set cookies, change status and set additional headers in web responses.
    """
    def __init__(self):
        self.headers: Dict[str, str] = {}
        self.cookies: Dict[str, Tuple[str, tuple, dict]] = {}
        self.del_cookies: List[Tuple[str, tuple, dict]] = []
        self.status: Optional[int] = None
        self.file_response: Optional[Union[str, Path]] = None

    def set_header(self, name: str, value: Any):
        self.headers[name] = value

    def set_cookie(self, name: str, value: str, *args, **kwargs):
        self.cookies[name] = (value, args, kwargs)

    def del_cookie(self, name: str, *args, **kwargs):
        self.del_cookies.append((name, args, kwargs))

    def set_status(self, status: int):
        self.status = status

    def set_file_response(self, path: Union[str, Path]):
        self.file_response = path
