"""
Mock hooks for testing apps
"""

from typing import Optional, AsyncGenerator, Dict, AsyncIterator, Union, Mapping

from multidict import CIMultiDict


class MockField:
    """
    Replacement for field object to be used for testing form preprocess methods
    """

    def __init__(
        self,
        name: str,
        value: Union[str, dict],
        file_data: Optional[bytes] = None,
        headers: Optional[CIMultiDict] = None,
    ) -> None:
        self.name = name
        self._value = value
        self.filename = None if file_data is None else value
        self.file_data = file_data
        self.headers: Mapping = CIMultiDict(
            {
                "Content-Type": (
                    "application/json"
                    if isinstance(value, dict)
                    else (
                        "application/octect-stream"
                        if file_data is not None
                        else "text/plain"
                    )
                )
            }
        )

    async def text(self):
        if isinstance(self._value, str):
            return self._value
        raise TypeError("field value must be str")

    async def json(self):
        if isinstance(self._value, dict):
            return self._value
        raise TypeError("field value must be dict")

    def __repr__(self):
        return (
            f"{type(self).__name__}(name={self.name}, value={self._value}, filename={self.filename}, "
            f"file_data={None if self.file_data is None else self.file_data[0:min(len(self.file_data), 10)]}...)"
        )


class MockFileHook:
    """
    Replacement for multipart file upload
    """

    def __init__(self, *, name: str, file_name: str, data: MockField):
        assert data.file_data is not None
        self.name = name
        self.file_name = file_name
        self.file_data = data.file_data
        self.size = len(data.file_data)
        self.done = False
        self.position = 0

    async def read_chunks(self, *, chunk_size: int = 16) -> AsyncGenerator[bytes, None]:
        if self.file_data is None:
            return
        for i in range(0, len(self.file_data), chunk_size):
            yield self.file_data[i : min(len(self.file_data), i + chunk_size)]  # noqa: E203

    async def read(self, chunk_size: int = -1) -> bytes:
        """
        File like object read function

        :param chunk_size: Size in bytes of each chunk.
            If chunk_size > 0 read will return a part of upcoming file of chunk_size size
            If chunk_size = -1, None or negative, read will return up to the end of the file
            If chunk_size = 0 read will return empty bytes
        :return bytes
        """
        if self.position >= self.size - 1:
            return b""
        if chunk_size > 0:
            current = self.position
            self.position = current + chunk_size
            return self.file_data[current : self.position]  # noqa: E203
        if chunk_size == -1:
            current = self.position
            self.position = self.size
            return self.file_data[current:]
        return b""


class MockMultipartReader:
    """
    Replacement for Multipart reader
    """

    def __init__(self, fields: Dict[str, str], attachments: Dict[str, bytes]):
        self.fields = fields
        self.it = iter(
            [
                MockField(name=k, value=v, file_data=attachments.get(k))
                for k, v in fields.items()
            ]
        )

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
