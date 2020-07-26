import asyncio
import time
import logging
from copy import copy
from asyncio import Lock
from typing import Dict, List, Tuple, Optional

import aioredis

from hopeit.app.context import EventContext
from hopeit.app.events import Spawn, SHUFFLE
from hopeit.app.logger import app_extra_logger

from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler
from hopeit.redis_mon import LogEventData, LogBatch


logger, extra = app_extra_logger()

__steps__ = ['process_log_data']

files = {}
redis: Optional[aioredis.Redis] = None


async def __init_event__(context: EventContext):
    global redis
    logger.info(context, "Connecting monitoring plugin...")
    redis = await aioredis.create_redis('redis://localhost:6379')


class FsHandler(FileSystemEventHandler):

    def __init__(self):
        self.batch = []
        self.lock = Lock()

    def on_any_event(self, event):
        try:
            src_path = event.src_path
            if files.get(src_path) is None:
                files[src_path] = open(src_path, 'r')
            line = files[src_path].readline()
            while line:
                asyncio.run(self._emit(line))
                line = files[src_path].readline()
        except Exception as e:
            print(e)

    async def _emit(self, line: str):
        try:
            await self.lock.acquire()
            self.batch.append(line)
        finally:
            self.lock.release()

    async def get_and_reset(self):
        # TODO: Sync
        try:
            await self.lock.acquire()
            results = self.batch
            self.batch = []
            return results
        finally:
            self.lock.release()


async def __service__(context: EventContext) -> Spawn[LogBatch]:
    path = context.env['log_reader']['path']
    event_handler = FsHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            await asyncio.sleep(3)
            yield LogBatch(data=await event_handler.get_and_reset())
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _parse_extras(extras: List[str]) -> Dict[str, str]:
    items = {}
    for entry in extras:
        entry = entry.strip('\n')
        if entry:
            k, v = entry.split('=')
            items[k] = v
    return items


async def process_log_data(payload: LogBatch, context: EventContext):
    assert redis, "No hay redis"
    print('==============================================================')
    for entry in payload.data:
        x = entry.split(' | ')
        ts, level, app_info, msg, extras = x[0], x[1], x[2], x[3], x[4:]
        app_name, app_version, event_name, host_name, pid = app_info.split(' ')
        extra_items = _parse_extras(extras)
        print(app_name, app_version, msg, extra_items.get('track.request_id'))
        print('-------------------------')
        req_id = extra_items.get('track.request_id')
        if req_id and msg in ['START', 'DONE', 'FAILED']:
            res = await redis.incr(f'{req_id}_{msg}')  # TODO: set TTL to 24h
            await redis.expire(f'{req_id}_{msg}', 20)
            print(f'{req_id}_{msg}', res)
    print('==============================================================')
