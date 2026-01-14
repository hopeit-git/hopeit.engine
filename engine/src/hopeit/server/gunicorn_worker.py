"""
Custom gunicorn workers for aiohttp with safe event loop initialization.
"""

from __future__ import annotations

import asyncio

from aiohttp.worker import GunicornWebWorker as AiohttpGunicornWebWorker
from gunicorn.workers.base import Worker as GunicornWorker


def _close_event_loop_if_present() -> None:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return
    loop.close()


class GunicornWebWorker(AiohttpGunicornWebWorker):
    def init_process(self) -> None:
        # Python 3.12+ raises if no loop is set; close only when present.
        _close_event_loop_if_present()

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        GunicornWorker.init_process(self)


class GunicornUVLoopWebWorker(AiohttpGunicornWebWorker):
    def init_process(self) -> None:
        import uvloop

        # Keep the same behavior as aiohttp's worker, but tolerate no loop.
        _close_event_loop_if_present()
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        GunicornWorker.init_process(self)
