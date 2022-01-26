import pytest

from hopeit.app.context import PreprocessFileHook, PreprocessHook
from hopeit.testing.hooks import MockMultipartReader, MockFileHook


class MockData:

    def __init__(self):
        self.chunks = [b'testdata'] * 4

    async def read_chunk(self, size: int) -> bytes:
        return self.chunks.pop() if len(self.chunks) > 0 else b''


@pytest.mark.asyncio
async def test_preprocess_file_hook_read_chunks():
    attachment_data = b'testdatatestdatatestdatatestdata'
    reader = MockData()
    hook = PreprocessFileHook(name="test_name", file_name="test_file_name", data=reader)
    data = b''
    async for chunk in hook.read_chunks(chunk_size=8):
        data += chunk
    assert data == attachment_data


@pytest.mark.asyncio
async def test_preprocess_file_hook_read_chunked():
    attachment_data = b'testdatatestdatatestdatatestdata'
    reader = MockData()
    hook = PreprocessFileHook(name="test_name", file_name="test_file_name", data=reader)
    data = b''
    chunck = await hook.read(chunk_size=8)
    while chunck:
        data += chunck
        chunck = await hook.read(chunk_size=8)
    assert data == attachment_data


@pytest.mark.asyncio
async def test_preprocess_file_hook_read_ones():
    attachment_data = b'testdatatestdatatestdatatestdata'
    reader = MockData()
    hook = PreprocessFileHook(name="test_name", file_name="test_file_name", data=reader)
    data = await hook.read(chunk_size=-1)
    assert data == attachment_data


@pytest.mark.asyncio
async def test_preprocess_file_hook_read_none():
    reader = MockData()
    hook = PreprocessFileHook(name="test_name", file_name="test_file_name", data=reader)
    data = await hook.read(chunk_size=0)
    assert data == b''


@pytest.mark.asyncio
async def test_preprocess_hook():
    attachment_data = b'testdatatestdatatestdatatestdata'
    fields = {'a': 'field-a', 'b': 'field-b', 'file-a': 'filename-a', 'file-b': 'filename-b',
              'c': {"name": "field-c"}}
    attachments = {'file-a': attachment_data, 'file-b': attachment_data}
    reader = MockMultipartReader(fields=fields, attachments=attachments)
    hook = PreprocessHook(
        headers={},
        multipart_reader=reader,
        file_hook_factory=MockFileHook
    )

    file_data = {'file-a': b'', 'file-b': b''}
    async for file in hook.files():
        assert file.file_name == fields[file.name]
        async for chunk in file.read_chunks():
            file_data[file.name] += chunk

    assert file_data == attachments

    args = await hook.parsed_args()
    assert args == fields


async def test_preprocess_hook_parsed_args():
    fields = {'a': 'field-a', 'b': 'field-b'}
    reader = MockMultipartReader(fields=fields, attachments={})
    hook = PreprocessHook(
        headers={},
        multipart_reader=reader,
        file_hook_factory=MockFileHook
    )
    args = await hook.parsed_args()
    assert args == fields
