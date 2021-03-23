"""
Mock hooks for testing apps
"""
from typing import Optional, AsyncGenerator, Dict, AsyncIterator, Union

from multidict import CIMultiDict


class MockField:
    """
    Replacement for field object to be used for testing form preprocess methods
    """
    def __init__(self, name: str, value: Union[str, dict], file_data: Optional[bytes] = None,
                 headers: Optional[CIMultiDict] = None) -> None:
        self.name = name
        self._value = value
        self.filename = None if file_data is None else value
        self.file_data = file_data
        self.headers = CIMultiDict({
            'Content-Type': 'application/json' if isinstance(value, dict)
            else 'application/octect-stream' if file_data is not None
            else 'text/plain'
        })

    async def text(self):
        if isinstance(self._value, str):
            return self._value
        raise TypeError("field value must be str")

    async def json(self):
        if isinstance(self._value, dict):
            return self._value
        raise TypeError("field value must be dict")

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, value={self._value}, filename={self.filename}, " \
               f"file_data={None if self.file_data is None else self.file_data[0:min(len(self.file_data),10)]}...)"


class MockFileHook:
    """
    Replacement for multipart file upload
    """
    def __init__(self, *, name: str, file_name: str, data: MockField):
        self.name = name
        self.file_name = file_name
        self.file_data = data.file_data
        self.size = 0

    async def read_chunks(self, *, chunk_size: int = 16) -> AsyncGenerator[bytes, None]:
        if self.file_data is None:
            return
        for i in range(0, len(self.file_data), chunk_size):
            yield self.file_data[i:min(len(self.file_data), i+chunk_size)]


class MockMultipartReader:
    """
    Replacement for Multipart reader
    """
    def __init__(self, fields: Dict[str, str], attachments: Dict[str, bytes]):
        self.fields = fields
        self.it = iter([
            MockField(name=k, value=v, file_data=attachments.get(k))
            for k, v in fields.items()
        ])

    def __aiter__(self) -> AsyncIterator[MockField]:
        return self  # type: ignore

    async def __anext__(self) -> MockField:
        try:
            part = next(self.it)
        except StopIteration:
            raise StopAsyncIteration  # pylint: disable=raise-missing-from
        return part

    async def next(self) -> MockField:
        return next(self.it)

    async def read_chunk(self, size: int) -> bytes:
        raise NotImplementedError()
