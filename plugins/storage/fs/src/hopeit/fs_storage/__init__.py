"""
Storage/persistence asynchronous stores and gets dataobjects from filesystem.

"""
import os
from glob import glob
from pathlib import Path
import uuid
from typing import Optional, Type, Generic, List

import aiofiles  # type: ignore
import aiofiles.os  # type: ignore

from hopeit.dataobjects import dataobject, DataObject
from hopeit.dataobjects.payload import Payload
from hopeit.fs_storage.partition import get_partition_key

__all__ = ['FileStorage',
           'FileStorageSettings']

SUFFIX = '.json'


@dataobject
class FileStorageSettings:
    """
    File storage plugin config

    :field: path, str: base path in file systems here data is saved
    :field: partition_dateformat, optional str: date format to be used to prefix file name in order
        to parition saved files to different subfolders based on event_ts(). i.e. "%Y/%m/%d"
        will store each files in a folder `base_path/year/month/day/`
    :field: flush_seconds, float: number of seconds to trigger a flush event to save all current
        buffered partitions. Default 0 means flish is not triggered by time.
    :field: fllush_max_size: max number of elements to keep in a partition before forcing a flush.
        Default 1. A value of 0 will disable flushing by partition size.
    """
    path: str
    partition_dateformat: Optional[str] = None
    flush_seconds: float = 0.0
    flush_max_size: int = 1


@dataobject
class ItemLocator:
    item_id: str
    partition_key: Optional[str] = None


class FileStorage(Generic[DataObject]):
    """
        Stores and retrieves dataobjects from filesystem
    """
    def __init__(self, *, path: str, partition_dateformat: Optional[str] = None):
        """
        Setups a file storage

        :param path: str, base path to be used to store and retrieve objects
        """
        self.path: Path = Path(path)
        os.makedirs(self.path.resolve().as_posix(), exist_ok=True)
        self.partition_dateformat = (partition_dateformat or '').strip('/')

    @classmethod
    def with_settings(cls, settings: FileStorageSettings) -> "FileStorage":
        return cls(
            path=settings.path,
            partition_dateformat=settings.partition_dateformat
        )

    async def list_objects(self, wildcard: str = '*') -> List[ItemLocator]:
        """
        Retrieves list of objects keys from the file storage

        :param wilcard: allow filter the listing of objects
        :return: List of objects key
        """
        base_path = str(self.path.resolve())
        path = base_path + '/' + wildcard + SUFFIX
        n_part_comps = len(self.partition_dateformat.split('/'))
        return [
            self._get_item_locator(item_path, n_part_comps) for item_path in glob(path)
        ]

    def _get_item_locator(self, item_path: str, n_part_comps: int) -> ItemLocator:
        comps = item_path.split("/")
        if self.partition_dateformat:
            partition_key = '/'.join(comps[-n_part_comps - 1:-1])
        else:
            partition_key = None
        return ItemLocator(
            item_id=comps[-1][:-len(SUFFIX)],
            partition_key=partition_key
        )

    async def get(
        self, key: str,
        *, datatype: Type[DataObject],
        partition_key: Optional[str] = None
    ) -> Optional[DataObject]:
        """
        Retrieves value under specified key, converted to datatype

        :param key: str
        :param datatype: class implementing @dataobject (@see DataObject)
        :param parition_key: partition path to be appended to base path
        :return: instance of datatype or None if not found
        """
        path = self.path / partition_key if partition_key else self.path
        payload_str = await self._load_file(path=path, file_name=key + SUFFIX)
        if payload_str:
            return Payload.from_json(payload_str, datatype)
        return None

    async def store(self, key: str, value: DataObject) -> str:
        """
        Stores value under specified key

        :param key: str
        :param value: DataObject, object annotated with @dataobject
        :return: str, path where the object was stored
        """
        payload_str = Payload.to_json(value)
        path = self.path
        if self.partition_dateformat:
            path = path / get_partition_key(value, self.partition_dateformat)
            os.makedirs(path.resolve().as_posix(), exist_ok=True)
        return await self._save_file(payload_str, path=path, file_name=key + SUFFIX)

    async def delete(self, *keys: str, partition_key: Optional[str] = None):
        """
        Delete specified keys

        :param keys: str, keys to be deleted
        """
        path = self.path / partition_key if partition_key else self.path
        for key in keys:
            await aiofiles.os.remove(path / (key + SUFFIX))

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
        async with aiofiles.open(tmp_path, 'w') as f:  # type: ignore
            await f.write(payload_str)
            await f.flush()
        os.rename(str(tmp_path), str(file_path))
        return str(file_path)
