"""
Webrunner module based on gunicorn
"""

import asyncio
from typing import List, Optional
import multiprocessing
from aiohttp.worker import GunicornWebWorker as AiohttpGunicornWebWorker
import gunicorn.app.base  # type: ignore
from gunicorn.workers.base import Worker as GunicornWorker

from hopeit.server.web import init_web_server


def number_of_workers() -> int:
    return (multiprocessing.cpu_count() * 2) + 1


def _ensure_loop() -> asyncio.AbstractEventLoop:
    # Ensure a asyncio loop exists (for gunicorn/uvloop)
    try:
        loop = asyncio.get_event_loop()
        loop.close()
    except RuntimeError:
        pass
    return asyncio.new_event_loop()


class GunicornWebWorker(AiohttpGunicornWebWorker):
    def init_process(self) -> None:
        # Python 3.12+ raises if no loop is set; close only when present.
        self.loop = _ensure_loop()
        asyncio.set_event_loop(self.loop)

        GunicornWorker.init_process(self)


class GunicornUVLoopWebWorker(AiohttpGunicornWebWorker):
    def init_process(self) -> None:
        import uvloop

        # Keep the same behavior as aiohttp's worker, but tolerate no loop.
        self.loop = _ensure_loop()
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        asyncio.set_event_loop(self.loop)

        GunicornWorker.init_process(self)


class WSGIApplication(gunicorn.app.base.BaseApplication):
    """
    WSGI HTTP Server
    """

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def run_app(
    host: str,
    port: int,
    path: Optional[str],
    config_files: List[str],
    api_file: str,
    api_auto: List[str],
    start_streams: bool,
    enabled_groups: List[str],
    workers: int,
    worker_class: str,
    worker_timeout: int,
):
    """
    Gunicorn Web Runner
    """
    workers = max(1, min(workers, number_of_workers()))

    bind = f"{host if host else '0.0.0.0'}:{port}"

    # Map known short names to Hopeit workers, accept full dotted paths, otherwise default to aiohttp workers.
    if worker_class == "GunicornWebWorker":
        resolved_worker_class = "hopeit.server.wsgi.GunicornWebWorker"
    elif worker_class == "GunicornUVLoopWebWorker":
        resolved_worker_class = "hopeit.server.wsgi.GunicornUVLoopWebWorker"
    elif "." in worker_class:
        resolved_worker_class = worker_class
    else:
        resolved_worker_class = f"aiohttp.{worker_class}"

    options = {
        "bind": bind,
        "workers": workers,
        "worker_class": resolved_worker_class,
        "proc_name": "hopeit_server",
        "timeout": worker_timeout,
    }
    if path:
        options["bind"] = f"unix:{path}"

    app = init_web_server(
        config_files=config_files,
        api_file=api_file,
        api_auto=api_auto,
        enabled_groups=enabled_groups,
        start_streams=start_streams,
    )

    WSGIApplication(app, options).run()
