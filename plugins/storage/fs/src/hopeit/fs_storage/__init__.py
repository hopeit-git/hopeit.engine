"""
Storage/persistence asynchronous stores and gets dataobjects from filesystem.

"""

import io
import os
import shutil
from glob import glob
from pathlib import Path
import uuid
from typing import Optional, Type, Generic, List

import aiofiles
import aiofiles.os

from hopeit.dataobjects import DataObject, dataclass, dataobject
from hopeit.dataobjects.payload import Payload
from hopeit.fs_storage.partition import get_file_partition_key, get_partition_key

__all__ = ["FileStorage", "FileStorageSettings"]

SUFFIX = ".json"


@dataobject
@dataclass
class FileStorageSettings:
    """
    File storage plugin config

    :field: path, str: base path in file systems here data is saved
    :field: partition_dateformat, optional str: date format to be used to prefix file name in order
        to partition saved files to different subfolders based on event_ts(). i.e. "%Y/%m/%d"
        will store each files in a folder `base_path/year/month/day/`
    :field: flush_seconds, float: number of seconds to trigger a flush event to save all current
        buffered partitions. Default 0 means flush is not triggered by time.
    :field: flush_max_size: max number of elements to keep in a partition before forcing a flush.
        Default 1. A value of 0 will disable flushing by partition size.
    """

    path: str
    partition_dateformat: Optional[str] = None
    flush_seconds: float = 0.0
    flush_max_size: int = 1


@dataobject
@dataclass
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
        self.partition_dateformat = (partition_dateformat or "").strip("/")

    @classmethod
    def with_settings(cls, settings: FileStorageSettings) -> "FileStorage":
        return cls(
            path=settings.path, partition_dateformat=settings.partition_dateformat
        )

    async def get(
        self,
        key: str,
        *,
        datatype: Type[DataObject],
        partition_key: Optional[str] = None,
    ) -> Optional[DataObject]:
        """
        Retrieves value under specified key, converted to datatype

        :param key: str
        :param datatype: dataclass implementing @dataobject (@see DataObject)
        :param partition_key: partition path to be appended to base path
        :return: instance of datatype or None if not found
        """
        path = self.path / partition_key if partition_key else self.path
        payload_str = await self._load_file(path=path, file_name=key + SUFFIX)
        if payload_str:
            return Payload.from_json(payload_str, datatype)
        return None

    async def get_file(
        self,
        file_name: str,
        *,
        partition_key: Optional[str] = None,
    ) -> Optional[bytes]:
        """
        Retrieves bytes for the specified file_name.

        :param file_name: str
        :param partition_key: Optional[str] partition path to be appended to base path
        :return: bytes, the content of the file as bytes, or None if the file is not found.
        """
        path = self.path / partition_key if partition_key else self.path
        file_path = path / file_name
        try:
            async with aiofiles.open(file_path, "rb") as file:
                return await file.read()
        except FileNotFoundError:
            return None

    async def store(self, key: str, value: DataObject) -> str:
        """
        Stores value under specified key

        :param key: str
        :param value: DataObject, instance of dataclass annotated with @dataobject
        :return: str, path where the object was stored
        """
        payload_str = Payload.to_json(value)
        path = self.path
        if self.partition_dateformat:
            path = path / get_partition_key(value, self.partition_dateformat)
            os.makedirs(path.resolve().as_posix(), exist_ok=True)
        return await self._save_file(payload_str, path=path, file_name=key + SUFFIX)

    async def store_file(self, file_name: str, value: io.BytesIO) -> str:
        """
        Stores a file-like object.

        :param file_name: str
        :param value: io.BytesIO, the file-like object to store
        :return: str file location
        """
        path = self.path
        partition_key = ""
        if self.partition_dateformat:
            partition_key = get_file_partition_key(self.partition_dateformat)
            path = path / partition_key
            os.makedirs(path.resolve().as_posix(), exist_ok=True)
        file_path = path / file_name
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(value.read())
            return file_path.as_posix()

    async def list_objects(self, wildcard: str = "*") -> List[ItemLocator]:
        """
        Retrieves list of objects keys from the file storage

        :param wildcard: allow filter the listing of objects
        :return: List of objects key
        """
        base_path = str(self.path.resolve())
        path = base_path + "/" + wildcard + SUFFIX
        n_part_comps = len(self.partition_dateformat.split("/"))
        return [
            self._get_item_locator(item_path, n_part_comps, SUFFIX)
            for item_path in glob(path)
        ]

    async def list_files(self, wildcard: str = "*") -> List[ItemLocator]:
        """
        Retrieves list of objects keys from the file storage

        :param wildcard: allow filter the listing of objects
        :return: List of objects key
        """
        base_path = str(self.path.resolve())
        path = base_path + "/" + wildcard
        n_part_comps = len(self.partition_dateformat.split("/"))
        return [
            self._get_item_locator(item_path, n_part_comps) for item_path in glob(path)
        ]

    async def delete(self, *keys: str, partition_key: Optional[str] = None):
        """
        Delete specified keys

        :param keys: str, keys to be deleted
        """
        path = self.path / partition_key if partition_key else self.path
        for key in keys:
            await aiofiles.os.remove(path / (key + SUFFIX))

    async def delete_files(self, *file_names: str, partition_key: Optional[str] = None):
        """
        Delete specified file_names

        :param file_names: str, file names to be deleted
        """
        path = self.path / partition_key if partition_key else self.path
        for file in file_names:
            await aiofiles.os.remove(path / file)

    def partition_key(self, path: str) -> str:
        """
        Get the partition key for a given path.

        :param path: str
        :return str, the extracted partition key.
        """
        partition_key = ""
        dir_name = os.path.dirname(path)
        if self.partition_dateformat:
            partition_key = dir_name.replace(self.path.as_posix(), "", 1).lstrip("/")
        return partition_key

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
        async with aiofiles.open(tmp_path, "w") as f:  # type: ignore
            await f.write(payload_str)
            await f.flush()
        shutil.move(str(tmp_path), str(file_path))
        return file_path.as_posix()

    def _get_item_locator(
        self, item_path: str, n_part_comps: int, suffix: Optional[str] = None
    ) -> ItemLocator:
        """This method generates an `ItemLocator` object from a given `item_path`"""
        comps = item_path.split("/")
        partition_key = (
            "/".join(comps[-n_part_comps - 1: -1])
            if self.partition_dateformat
            else None
        )
        item_id = comps[-1][: -len(suffix)] if suffix else comps[-1]
        return ItemLocator(item_id=item_id, partition_key=partition_key)
