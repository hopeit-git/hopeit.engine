import pytest  # type: ignore
import os
from dataclasses import dataclass

import aiofiles  # type: ignore

from hopeit.dataobjects import dataobject
from hopeit.toolkit.storage.fs import FileStorage


@dataobject
@dataclass
class FsMockData:
    test: str


payload_str = """{"test":"test_fs"}"""
test_fs = FsMockData(test='test_fs')


async def save_and_load_file(payload):
    key = "VALIDFILE"
    fs = FileStorage(path=f"/tmp/{key}/")
    path = await fs.store(key, test_fs)
    assert path == f'/tmp/{key}/{key}.json'
    loaded = await fs.get(key, datatype=FsMockData)
    assert loaded == test_fs
    assert type(loaded) is FsMockData


async def load_missing_file():
    key = "FILENOTFOUND"
    fs = FileStorage(path=f"/tmp/{key}/")
    loaded = await fs.get(key, datatype=FsMockData)
    assert loaded is None


class MockFile:
    def __init__(self, payload_str: str):
        self.payload_str = payload_str

    def __enter__(self):
        return self

    def __aenter__(self):
        return self

    def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.await_nothing()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def await_nothing(self):
        return self

    def __await__(self):
        return self.await_nothing().__await__()

    async def read(self):
        print('read', self.payload_str)
        return self.payload_str

    async def write(self, payload_str):
        print('write', self.payload_str)
        self.payload_str = payload_str

    async def flush(self):
        pass

    @staticmethod
    def open(path, mode='r'):
        assert path
        assert mode
        if "FILENOTFOUND" in str(path):
            raise FileNotFoundError(str(path))
        elif "VALIDFILE" in str(path):
            return MockFile(payload_str)
        else:
            raise NotImplementedError()


class MockPath:
    @staticmethod
    def exists(path):
        assert path
        return False


class MockOs:
    @staticmethod
    def rename(source, dest):
        pass

    @staticmethod
    def makedirs(path, mode=None, exist_ok=False):
        pass


@pytest.mark.asyncio
async def test_load_file(monkeypatch):
    monkeypatch.setattr(aiofiles, 'open', MockFile.open)
    monkeypatch.setattr(os, 'makedirs', MockOs.makedirs)
    monkeypatch.setattr(os.path, 'exists', MockPath.exists)
    monkeypatch.setattr(os, 'rename', MockOs.rename)
    await save_and_load_file(payload_str)


@pytest.mark.asyncio
async def test_load_missing_file(monkeypatch):
    monkeypatch.setattr(aiofiles, 'open', MockFile.open)
    await load_missing_file()
