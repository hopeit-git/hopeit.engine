from typing import Optional, AsyncGenerator, Dict, AsyncIterator


class MockField:
    def __init__(self, name: str, value: str, file_data: Optional[bytes] = None) -> None:
        self.name = name
        self._value = value
        self.filename = None if file_data is None else value
        self.file_data = file_data

    async def text(self):
        return self._value

    def __repr__(self):
        return f"{type(self).__name__}(name={self.name}, value={self._value}, filename={self.filename}, " \
               f"file_data={None if self.file_data is None else self.file_data[0:min(len(self.file_data),10)]}...)"


class MockFileHook:
    def __init__(self, *, name: str, file_name: str, data: MockField):
        self.name = name
        self.file_name = file_name
        self.file_data = data.file_data
        self.size = 0

    async def read_chunks(self, *, chunk_size: int = 16) -> AsyncGenerator[bytes, None]:
        for i in range(0, len(self.file_data), chunk_size):
            yield self.file_data[i:min(len(self.file_data), i+chunk_size)]


class MockMultipartReader:
    def __init__(self, fields: Dict[str, str], attachments: Dict[str, bytes]):
        self.fields = fields
        self.it = iter([
            MockField(name=k, value=v, file_data=attachments.get(k))
            for k, v in fields.items()
        ])

    def __aiter__(self) -> AsyncIterator["MockField"]:
        return self  # type: ignore

    async def __anext__(self) -> Optional["MockMultipartReader"]:
        try:
            part = next(self.it)
        except StopIteration:
            raise StopAsyncIteration
        return part

    async def next(self) -> Optional["MockMultipartReader"]:
        return next(self.it)
