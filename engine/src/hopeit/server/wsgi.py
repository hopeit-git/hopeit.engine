"""
Webrunner module based on gunicorn
"""
from typing import List, Optional
from abc import abstractmethod
import multiprocessing
import gunicorn.app.base   # type: ignore

from hopeit.server.web import init_web_server


def number_of_workers() -> int:
    return (multiprocessing.cpu_count() * 2) + 1


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


def run_app(host: str, port: int, path: Optional[str], config_files: List[str], api_file: str, api_auto: List[str],
            start_streams: bool, enabled_groups: List[str], workers: int, worker_class: str, worker_timeout: int):
    """
    Gunicorn Web Runner
    """
    workers = max(1, min(workers, number_of_workers()))

    bind = f"{host if host else '0.0.0.0'}:{port}"

    options = {
        'bind': bind,
        'workers': workers,
        'worker_class': f'aiohttp.{worker_class}',
        'proc_name': 'hopeit_server',
        'timeout': worker_timeout
    }
    if path:
        options['bind'] = f'unix:{path}'

    app = init_web_server(
            config_files=config_files,
            api_file=api_file,
            api_auto=api_auto,
            enabled_groups=enabled_groups,
            start_streams=start_streams)

    WSGIApplication(app, options).run()
