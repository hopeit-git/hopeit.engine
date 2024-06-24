import logging
import subprocess
import sys
import os
from time import sleep
from typing import List, Optional

import pytest
from click.testing import CliRunner
from hopeit.cli.server import run
from hopeit.server import wsgi


def run_app(host: str, port: int, path: Optional[str], config_files: List[str], api_file: str, api_auto: List[str],
            start_streams: bool, enabled_groups: List[str], workers: int, worker_class: str, worker_timeout: int):
    print(f"Listening at: http://{host}:{port}")


class MockBaseAppliction:
    def __init__(self, app, options=None):
        pass

    @staticmethod
    def run():
        print("Listening at: http://localhost:8021")


async def test_example_app_starts_ok(monkeypatch):
    sys.path.append("plugins/auth/basic-auth/src/")
    sys.path.append("apps/examples/simple-example/src/")
    sys.path.append("plugins/storage/fs/src/")
    sys.path.append("plugins/ops/config-manager/src/")

    runner = CliRunner()
    wsgi.WSGIApplication = MockBaseAppliction
    result = runner.invoke(run, [
        "--port=8021",
        "--config-files=engine/config/dev-local.json"
        ",plugins/auth/basic-auth/config/plugin-config.json"
        ",plugins/ops/config-manager/config/plugin-config.json"
        ",apps/examples/simple-example/config/app-config.json",
        "--api-file=apps/examples/simple-example/api/openapi.json",
        "--enabled-groups=g1,g2"])
    assert result.exit_code == 0
    assert result.output == "Listening at: http://localhost:8021\n"


def test_missing_config_files(monkeypatch):
    runner = CliRunner()
    result = runner.invoke(run, ["--port=8021",
                                 "--api-file=apps/examples/simple-example/api/openapi.json",
                                 "--enabled-groups=g1,g2"])
    assert result.exit_code == 2
    assert result.output == "Usage: run [OPTIONS]\nTry 'run --help' for help.\n\n" \
                            "Error: Missing option '--config-files'.\n"


def test_empty_config_files(monkeypatch):
    runner = CliRunner()
    result = runner.invoke(run, ["--port=8021",
                                 "--config-files"])
    assert result.exit_code == 2
    assert result.output == "Error: Option '--config-files' requires an argument.\n"


def test_default_host_port(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(wsgi, 'run_app', run_app)
    result = runner.invoke(run, ["--config-files=engine/config/dev-local.json"
                                 ",plugins/auth/basic-auth/config/plugin-config.json"])
    assert result.exit_code == 0
    assert result.output == "Listening at: http://0.0.0.0:8020\n"


def test_custom_host_port(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(wsgi, 'run_app', run_app)
    result = runner.invoke(run, ["--port=8888", "--host=myhost.mydomain",
                                 "--config-files=engine/config/dev-local.json"
                                 ",plugins/auth/basic-auth/config/plugin-config.json"])
    assert result.exit_code == 0
    assert result.output == "Listening at: http://myhost.mydomain:8888\n"


@pytest.mark.parametrize("worker_class", ["GunicornWebWorker", "GunicornUVLoopWebWorker"])
def test_hopeit_server(worker_class):
    """ Test hopeit_server running in a subprocess """

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    hopeit_proc = None
    proc_output = None

    args = ["python", "-m", "hopeit.cli.server", "run",
            "--config-files=engine/config/dev-local.json"
            ",plugins/auth/basic-auth/config/plugin-config.json",
            f"--worker-class={worker_class}"]

    mock_env = os.environ.copy()
    mock_env["PYTHONPATH"] = "plugins/auth/basic-auth/src/:" + mock_env["PYTHONPATH"]

    hopeit_proc = subprocess.Popen(args, env=mock_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sleep(2)
    hopeit_proc.terminate()

    while hopeit_proc.poll() is None:
        proc_output = hopeit_proc.stdout.read().decode()
        sleep(1)

    logger.info("\n%s", proc_output)
    assert hopeit_proc.returncode == 0
    assert "[ERROR]" not in proc_output
    assert "Listening at: http://0.0.0.0:8020" in proc_output
    assert "/decode | \n[" in proc_output
    assert "[INFO] Shutting down: Master" in proc_output
