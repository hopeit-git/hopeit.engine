"""
Webrunner module based on gunicorn
"""
from typing import List
from abc import abstractmethod
from dataclasses import dataclass
import multiprocessing

from aiohttp import web
import gunicorn.app.base   # type: ignore

from hopeit.server.web import init_web_server


@dataclass
class AppConfig():
    config_files: List[str]
    api_file: str
    enabled_groups: List[str]
    start_streams: bool


app_config: AppConfig


def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


async def wsgi_app() -> web.Application:
    return init_web_server(
        config_files=app_config.config_files,
        api_file=app_config.api_file,
        enabled_groups=app_config.enabled_groups,
        start_streams=app_config.start_streams)


class WSGIApplication(gunicorn.app.base.BaseApplication):
    """
    WSGI HTTP Server
    """
    @abstractmethod
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def run_app(host: str, port: int, config_files: List[str], api_file: str, start_streams: bool,
            enabled_groups: List[str], workers: int):
    """
    Gunicorn Web Runner
    """
    global app_config
    app_config = AppConfig(
        config_files=config_files,
        api_file=api_file,
        enabled_groups=enabled_groups,
        start_streams=start_streams)

    workerclass = 'aiohttp.GunicornWebWorker'
    # workerclass = 'aiohttp.GunicornUVLoopWebWorker'
    bind = f"{host if host else '127.0.0.1'}:{port}"

    options = {
        'bind': bind,
        'workers': workers,
        'worker_class': workerclass,
        'max_requests': 0,
        'proc_name': 'hopeit.engine',
        'graceful_timeout': 60,
    }

    WSGIApplication(wsgi_app, options).run()
