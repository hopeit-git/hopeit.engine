"""
Context information and handling
"""
from typing import AsyncGenerator, AsyncIterator, Callable, Generic, TypeVar, \
    Dict, Optional, Any, Tuple, Union, List
from abc import ABC
from pathlib import Path
from datetime import datetime, timezone

from multidict import CIMultiDict, CIMultiDictProxy, istr


from hopeit.app.config import AppConfig, AppDescriptor, EventDescriptor, Env, EventType


__all__ = ['EventContext',
           'PostprocessHook',
           'PreprocessHook',
           'NoopMultiparReader']


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
            'track.client_app_key',
            'track.client_event_name',
            *app_config.engine.track_headers,
            *(self.event_info.config.logging.stream_fields
              if self.event_info.type == EventType.STREAM
              else [])
        ]
        self.track_ids = {k: track_ids[k] for k in track_fields if k in track_ids}


class PostprocessHook():
    """
    Post process hook that keeps additional changes to add to response on
    `__postprocess__(...)` event methods.

    Useful to set cookies, change status and set additional headers in web responses.
    """
    def __init__(self):
        self.headers: Dict[str, str] = {}
        self.cookies: Dict[str, Tuple[str, tuple, dict]] = {}
        self.del_cookies: List[Tuple[str, tuple, dict]] = []
        self.status: Optional[int] = None
        self.file_response: Optional[Union[str, Path]] = None
        self.content_type: str = "application/json"

    def set_header(self, name: str, value: Any):
        self.headers[name] = value

    def set_content_type(self, content_type: str):
        self.content_type = content_type

    def set_cookie(self, name: str, value: str, *args, **kwargs):
        self.cookies[name] = (value, args, kwargs)

    def del_cookie(self, name: str, *args, **kwargs):
        self.del_cookies.append((name, args, kwargs))

    def set_status(self, status: int):
        self.status = status

    def set_file_response(self, path: Union[str, Path]):
        self.file_response = path


class BodyPartReaderProtocol(ABC):
    """
    Required functionallity for BodyPartReader implementation
    to be used in PreprocessHook
    """
    async def read_chunk(self, size: Optional[int] = None) -> bytes:
        ...

    async def text(self, *, encoding: Optional[str] = None) -> str:
        ...

    async def json(self, *, encoding: Optional[str] = None) -> Optional[Dict[str, Any]]:
        ...

    @property
    def name(self) -> Optional[str]:
        ...

    @property
    def filename(self) -> Optional[str]:
        ...

    @property
    def headers(self) -> CIMultiDictProxy[str]:
        ...


class MultipartReaderProtocol(ABC):
    """
    Required functionality for Mutipartreader implementation
    to be used in PreprocessHook
    """

    def __aiter__(
        self,
    ) -> AsyncIterator["BodyPartReaderProtocol"]:
        ...

    async def __anext__(
        self,
    ) -> Optional[Union["MultipartReaderProtocol", BodyPartReaderProtocol]]:
        ...


class NoopMultiparReader(MultipartReaderProtocol):
    pass


_MultipartReader = TypeVar('_MultipartReader', bound=MultipartReaderProtocol)
_BodyPartReader = TypeVar('_BodyPartReader', bound=BodyPartReaderProtocol)


class PreprocessFileHook(Generic[_BodyPartReader]):
    """
    Hook to read files from multipart requests
    """
    def __init__(self, *, name: str, file_name: str, data: _BodyPartReader):
        self.name = name
        self.file_name = file_name
        self.data = data
        self.size = 0

    async def read_chunks(self, *, chunk_size: int) -> AsyncGenerator[bytes, None]:
        chunk = await self.data.read_chunk(size=chunk_size)
        while chunk:
            self.size += len(chunk)
            yield chunk
            chunk = await self.data.read_chunk(size=chunk_size)


class PreprocessHeaders:
    """
    Wrapper to receive request headers in `__preprocess__` functions
    """
    def __init__(self, request_headers: CIMultiDictProxy[str]) -> None:
        self._headers = request_headers

    def __getitem__(self, key: str) -> Any:
        return self._headers[key]

    def get(self, key: str) -> Any:
        return self._headers.get(key)

    def __repr__(self):
        return self._headers.__repr__()

    @classmethod
    def from_dict(cls, data: Dict[str, str]):
        return cls(CIMultiDictProxy(CIMultiDict(data)))


class PreprocessHook(Generic[_MultipartReader]):
    """
    Preprocess hook that handles information available in the request to be accessed
    from `__preprocess__(...)` event method when defined.
    """
    def __init__(self, *, headers: CIMultiDictProxy[str],
                 multipart_reader: Optional[_MultipartReader] = None,
                 file_hook_factory: Callable = PreprocessFileHook):
        self.headers = PreprocessHeaders(headers)
        self._multipart_reader = multipart_reader
        self._args: Dict[str, Any] = {}
        self._iterated = False
        self.status: Optional[int] = None
        self.file_hook_factory = file_hook_factory

    def set_status(self, status: int):
        self.status = status

    async def parsed_args(self):
        if not self._iterated:
            async for _ in self.files():
                pass
        return self._args

    async def files(self) -> AsyncGenerator[Any, None]:
        """
        Iterator over attached files in multipart uploads
        """
        assert not self._iterated, "Request fields already extracted"
        self._iterated = True
        if self._multipart_reader is not None:
            async for field in self._multipart_reader:
                if field.name is not None:
                    if field.filename:
                        self._args[field.name] = field.filename
                        yield self.file_hook_factory(name=field.name, file_name=field.filename, data=field)
                    elif field.headers.get(istr("Content-Type")) == 'application/json':
                        self._args[field.name] = await field.json()
                    else:
                        self._args[field.name] = await field.text()
