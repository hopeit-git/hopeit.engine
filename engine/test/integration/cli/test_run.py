import subprocess
from time import sleep
from typing import Optional, List
import logging
import pytest
from click.testing import CliRunner
from hopeit.server import wsgi
from hopeit.cli.server import run


class MockHopeitWeb:
    @staticmethod
    def run_app(host: str, port: int, path: Optional[str], config_files: List[str], api_file: str,
                start_streams: bool, enabled_groups: List[str], workers: int, worker_class: str):
        print(f"Server running on port {port}")


class MockBaseAppliction:
    def __init__(self, app, options=None):
        pass

    @staticmethod
    def run():
        print("Server running on port 8021")


def test_full_signatre(monkeypatch):
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
    assert result.output == "Server running on port 8021\n"


def test_missing_config_files(monkeypatch):
    runner = CliRunner()
    wsgi.WSGIApplication = MockBaseAppliction
    result = runner.invoke(run, ["--port=8021",
                                 "--api-file=apps/examples/simple-example/api/openapi.json",
                                 "--enabled-groups=g1,g2"])
    assert result.exit_code == 2


def test_empty_config_files(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(wsgi, "run_app", MockHopeitWeb.run_app)
    result = runner.invoke(run, ["--port=8021",
                                 "--condig-files"])
    assert result.exit_code == 2


def test_default_port(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr(wsgi, 'run_app', MockHopeitWeb.run_app)
    result = runner.invoke(run, ["--config-files=engine/config/dev-local.json"
                                 ",plugins/auth/basic-auth/config/plugin-config.json"])
    assert result.exit_code == 0
    assert result.output == "Server running on port 8020\n"


@pytest.mark.parametrize("worker_class", ["GunicornWebWorker", "GunicornUVLoopWebWorker"])
def test_hopeit_server(worker_class):
    """ Test hopeit_server running in a subprocess """

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    hopeit_proc = None
    proc_output = None

    args = ["hopeit_server", "run",
            "--config-files=engine/config/dev-local.json"
            ",plugins/auth/basic-auth/config/plugin-config.json",
            f"--worker-class={worker_class}"]

    hopeit_proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
