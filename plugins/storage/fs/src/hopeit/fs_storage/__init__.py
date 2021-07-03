"""
Storage/persistence asynchronous stores and gets dataobjects from filesystem.

"""
import os
from glob import glob
from pathlib import Path
import uuid
from typing import Optional, Type, Generic, List

import aiofiles  # type: ignore

from hopeit.dataobjects import DataObject
from hopeit.dataobjects.payload import Payload

__all__ = ['FileStorage']

SUFFIX = '.json'


class FileStorage(Generic[DataObject]):
    """
        Stores and retrieves dataobjects from filesystem
    """
    def __init__(self, *, path: str):
        """
        Setups a file storage

        :param path: str, base path to be used to store and retrieve objects
        """
        self.path: Path = Path(path)

    async def list_objects(self, wildcard: str = '*') -> List[str]:
        """
        Retrieves list of objects keys from the file storage

        :param wilcard: allow filter the listing of objects
        :return: List of objects key
        """

        path = str(self.path.absolute()) + '/' + wildcard + SUFFIX
        return [Path(path).name[:-len(SUFFIX)] for path in glob(path)]

    async def get(self, key: str, *, datatype: Type[DataObject]) -> Optional[DataObject]:
        """
        Retrieves value under specified key, converted to datatype

        :param key: str
        :param datatype: dataclass implementing @dataobject (@see DataObject)
        :return: instance of datatype or None if not found
        """
        payload_str = await self._load_file(path=self.path, file_name=key + SUFFIX)
        if payload_str:
            return Payload.from_json(payload_str, datatype)
        return None

    async def store(self, key: str, value: DataObject) -> str:
        """
        Stores value under specified key

        :param key: str
        :param value: DataObject, instance of dataclass annotated with @dataobject
        :return: str, path where the object was stored
        """
        payload_str = Payload.to_json(value)
        return await self._save_file(payload_str, path=self.path, file_name=key + SUFFIX)

    @staticmethod
    async def _load_file(*, path: Path, file_name: str) -> Optional[str]:
        """
        Read contents from file `path/file_name` asynchronously.
        Returns string with contents or None is file is not found.
        """
        file_path = path / file_name
        try:
            async with aiofiles.open(file_path) as f:  # type: ignore
                return await f.read()
        except FileNotFoundError:
            return None

    @staticmethod
    async def _save_file(payload_str: str, *, path: Path, file_name: str) -> str:
        """
        Save `payload_str` to `path/file_name` asynchronously.
        First buffers and stores the file with a random hidden file name
        into the specified `path`, then when writing is finished
        it will rename the file to the desired name atomically.
        """
        file_path = path / file_name
        tmp_path = path / str(f".{uuid.uuid4()}")
        os.makedirs(str(path), exist_ok=True)
        async with aiofiles.open(tmp_path, 'w') as f:  # type: ignore
            await f.write(payload_str)
            await f.flush()
        os.rename(str(tmp_path), str(file_path))
        return str(file_path)
