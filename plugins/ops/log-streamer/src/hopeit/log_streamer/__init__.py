"""
Log Stramer dataclasses and file handler implementation based on watchdog library
"""
import asyncio
from typing import Dict, List, TextIO
from datetime import datetime

from watchdog.observers import Observer  # type: ignore
from watchdog.events import FileSystemEventHandler  # type: ignore

from hopeit.dataobjects import dataobject, dataclass
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit.fs_storage import FileStorage

logger, extra = app_extra_logger()


@dataobject
@dataclass
class LogReaderConfig:
    """
    Log reader config env section
    """
    logs_path: str
    prefix: str = ''
    checkpoint_path: str = 'log_streamer/checkpoints/'
    file_open_timeout_secs: int = 600
    file_checkpoint_expire_secs: int = 86400
    batch_size: int = 10000
    batch_wait_interval_secs: int = 1


@dataobject
@dataclass
class LogRawBatch:
    """
    Batch of raw lines read from logs
    """
    data: List[str]


@dataobject
@dataclass
class LogEntry:
    """
    Parsed log line
    """
    ts: str
    msg: str
    app_name: str
    app_version: str
    event_name: str
    event: str
    extra: Dict[str, str]
    host: str = ''
    pid: str = ''


@dataobject
@dataclass
class LogBatch:
    """
    Batch of parsed log entries
    """
    entries: List[LogEntry]


@dataobject
@dataclass
class Checkpoint:
    line: str
    expire: int


class LogFileHandler(FileSystemEventHandler):
    """
    LogFileHandler based on watchdog FileSystemEventHandler.

    This handler collects lines from changed log files and emit batches on demaand when
    `get_and_rest_batch` is called.
    It also keeps track of open files and ensures they are closed when inactive or deleted,
    allowing to work combined with `logrotate`.
    """
    EVENTS_SORT_ORDER = ['START', '', 'DONE', 'FAILED']

    def __init__(self, config: LogReaderConfig, context: EventContext):
        self.path = config.logs_path
        self.prefix = config.logs_path + config.prefix
        self.checkpoint_storage = FileStorage(path=config.checkpoint_path)  # type: ignore
        self.context = context
        self.batch: List[str] = []
        self.open_files: Dict[str, TextIO] = {}
        self.last_access: Dict[str, float] = {}
        self.loop = asyncio.get_event_loop()
        self.lock = asyncio.Lock()
        self.file_open_timeout = config.file_open_timeout_secs
        self.file_checkpoint_expire = config.file_checkpoint_expire_secs

    def on_moved(self, event):
        try:
            if event.src_path in self.open_files:
                self.last_access[event.src_path] = 0
                self.close_inactive_files()
        except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
            logger.error(self.context, e)

    def on_deleted(self, event):
        try:
            if event.src_path in self.open_files:
                self.last_access[event.src_path] = 0
                self.close_inactive_files()
        except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
            logger.error(self.context, e)

    def on_modified(self, event):
        try:
            if event.src_path.find(self.prefix) >= 0:
                asyncio.run_coroutine_threadsafe(self._on_event(event), self.loop)
        except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
            logger.error(self.context, e)

    def _add_line(self, lines: List[str], line: str):
        if ('| START |' in line) or ('| DONE |' in line) or ('| FAILED |' in line):
            lines.append(line)

    async def _on_event(self, event):
        """
        Collect log lines when a filesystem event is received
        """
        try:
            src_path = event.src_path
            if await self._open_file(src_path):
                line = await self._read_line(src_path)
                if line:
                    lines = []
                    self._add_line(lines, line)
                    while line:
                        line = await self._read_line(src_path)
                        self._add_line(lines, line)
                    if len(lines) > 0:
                        await self._emit(lines)
                        await self._save_checkpoint(src_path, lines[-1])
        except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
            logger.error(self.context, e)

    async def _save_checkpoint(self, src_path: str, line: str):
        async with self.lock:
            key = f'{self.context.app_key}.{src_path}.checkpoint'.replace('/', 'x')
            cp = Checkpoint(
                line=line,
                expire=int(datetime.now().timestamp()) + self.file_checkpoint_expire
            )
            await self.checkpoint_storage.store(key, cp)

    async def _load_checkpoint(self, src_path: str) -> str:
        key = f'{self.context.app_key}.{src_path}.checkpoint'.replace('/', 'x')
        cp = await self.checkpoint_storage.get(key, datatype=Checkpoint)
        if cp is None:
            return ''
        if int(cp.expire) < int(datetime.now().timestamp()):
            return ''
        return cp.line

    async def _open_file(self, src_path: str) -> bool:
        """
        Opens a log file and keeps track of it.
        If the file was read before lines already read will be skept using a saved checkpoint.
        """
        try:
            async with self.lock:
                self.last_access[src_path] = datetime.now().timestamp()
                if self.open_files.get(src_path) is None:
                    checkpoint = await self._load_checkpoint(src_path)
                    logger.info(self.context, "Opening log file...", extra=extra(
                        src_path=src_path, checkpoint=checkpoint
                    ))
                    self.open_files[src_path] = open(src_path, 'r')  # pylint: disable=consider-using-with
                    if checkpoint:
                        line = self.open_files[src_path].readline()
                        if line and (line <= checkpoint):
                            logger.info(self.context, "Skipping to checkpoint...", extra=extra(
                                src_path=src_path, checkpoint=checkpoint
                            ))
                            while line and (line[:24] < checkpoint[:24]):
                                line = self.open_files[src_path].readline()
                            while line and (line[:24] <= checkpoint[:24]) and (line != checkpoint):
                                line = self.open_files[src_path].readline()
                            logger.info(self.context, "Skip to checkpoint done.", extra=extra(
                                src_path=src_path, checkpoint=checkpoint
                            ))
                        else:
                            self.open_files[src_path].seek(0)
                return True
        except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
            logger.error(self.context, e)
            return False

    def close_inactive_files(self):
        """
        Closes files that are inactive (deleted of with no activity)
        """
        exp = datetime.now().timestamp()
        for key, last_ts in list(self.last_access.items()):
            if (last_ts + self.file_open_timeout) < exp:
                try:
                    logger.info(self.context, "Closing inactive/deleted file...", extra=extra(src_path=key))
                    if key in self.open_files:
                        self.open_files[key].close()
                        del self.open_files[key]
                except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
                    logger.error(self.context, e)
                del self.last_access[key]

    async def _read_line(self, src_path: str):
        return self.open_files[src_path].readline()

    async def _emit(self, lines: List[str]):
        async with self.lock:
            self.batch.extend(lines)

    async def get_and_reset_batch(self):
        """
        Returns current collected lines and clears buffer
        """
        def _sort_batch(x):
            xs = x.split(' | ')[:5]
            try:
                xs[3] = self.EVENTS_SORT_ORDER.index(xs[3])
            except ValueError:
                xs[3] = 1
            except IndexError:
                pass
            return tuple(xs)

        async with self.lock:
            results = sorted(self.batch, key=_sort_batch)
            self.batch = []
            return results


def start_observer(event_handler: LogFileHandler, logs_path: str) -> Observer:
    observer = Observer()
    observer.schedule(event_handler, logs_path, recursive=False)
    observer.start()
    return observer
