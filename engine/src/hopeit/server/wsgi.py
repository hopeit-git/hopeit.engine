"""
Webrunner module based on gunicorn
"""
from typing import List, Optional
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


def number_of_workers() -> int:
    return (multiprocessing.cpu_count() * 2) + 1


async def wsgi_app() -> web.Application:
    print(app_config.config_files)
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


def run_app(host: str, port: int, path: Optional[str], config_files: List[str], api_file: str, start_streams: bool,
            enabled_groups: List[str], workers: int, worker_class: str):
    """
    Gunicorn Web Runner
    """

    workers = max(1, min(workers, number_of_workers()))

    global app_config
    app_config = AppConfig(
        config_files=config_files,
        api_file=api_file,
        enabled_groups=enabled_groups,
        start_streams=start_streams)

    bind = f"{host if host else '0.0.0.0'}:{port}"
    print(bind)
    options = {
        'bind': bind,
        'workers': workers,
        'worker_class': f'aiohttp.{worker_class}',
        'proc_name': 'hopeit.engine',
        'logfile': './logfile.log'
    }
    if path:
        options['bind'] = f'unix:{path}'

    WSGIApplication(wsgi_app, options).run()
