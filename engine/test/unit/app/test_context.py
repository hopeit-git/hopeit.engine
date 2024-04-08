import pytest
from unittest.mock import MagicMock

from hopeit.app import context as context_mod
from hopeit.app.context import PostprocessHook, PreprocessFileHook, PreprocessHook
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
async def test_preprocess_file_hook_read_once():
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
async def test_preprocess_hook_read_chunks():
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


@pytest.mark.asyncio
async def test_preprocess_hook_read():
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
        chunk = await file.read(chunk_size=3)
        while chunk:
            file_data[file.name] += chunk
            chunk = await file.read(chunk_size=3)

    assert file_data == attachments

    args = await hook.parsed_args()
    assert args == fields


@pytest.mark.asyncio
async def test_preprocess_hook_read_once():
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
        file_data[file.name] = await file.read()
    assert file_data == attachments

    args = await hook.parsed_args()
    assert args == fields


@pytest.mark.asyncio
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


@pytest.mark.asyncio
async def test_postprocess_host_create_stream_response():
    hook = PostprocessHook()
    context = MagicMock()
    track_ids = {
        "track1": "id1",
        "track2": "id2"
    }
    context.track_ids = {
        **track_ids
    }
    stream_response = await hook.prepare_stream_response(
        context, "test-disposition", "test-type", 42
    )
    assert stream_response.headers['Content-Disposition'] == "test-disposition"
    assert stream_response.headers['Content-Type'] == "test-type"
    assert stream_response.resp.headers['Content-Disposition'] == "test-disposition"
    assert stream_response.resp.headers['Content-Type'] == "test-type"
    assert stream_response.resp.headers['Content-Length'] == "42"
    assert stream_response.resp.headers['X-Track1'] == "id1"
    assert stream_response.resp.headers['X-Track2'] == "id2"
    assert stream_response.resp.data == b''
    assert hook.content_type == "test-type"


class MockStreamResponse:
    def __init__(self, *, headers):
        self.headers = headers
        self.content_type = ''
        self.content_length = 0
        self.data = None

    async def prepare(self, request):
        self.data = b''

    async def write(self, data):
        self.data += data


@pytest.mark.asyncio
async def test_postprocess_host_create_web_stream_response(monkeypatch):

    monkeypatch.setattr(context_mod.web, "StreamResponse", MockStreamResponse)

    request = MagicMock()
    hook = PostprocessHook(request)
    context = MagicMock()
    track_ids = {
        "track1": "id1",
        "track2": "id2"
    }
    context.track_ids = {
        **track_ids
    }
    stream_response = await hook.prepare_stream_response(
        context, "test-disposition", "test-type", 42
    )
    assert stream_response.headers['Content-Disposition'] == "test-disposition"
    assert stream_response.headers['Content-Type'] == "test-type"
    assert stream_response.resp.content_type == "test-type"
    assert stream_response.resp.content_length == 42
    assert stream_response.resp.headers['X-Track1'] == "id1"
    assert stream_response.resp.headers['X-Track2'] == "id2"
    assert stream_response.resp.data == b''
    assert hook.content_type == "test-type"
