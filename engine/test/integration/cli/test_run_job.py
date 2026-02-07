import json
import logging
import os
import subprocess

import pytest
from click.testing import CliRunner

from hopeit.cli.job import job
from hopeit.dataobjects.payload import Payload
import hopeit.cli.job as cli_job


def test_missing_config_files():
    runner = CliRunner()
    result = runner.invoke(job, ["--event-name=test.event"])
    assert result.exit_code == 2
    assert (
        result.output == "Usage: job [OPTIONS]\nTry 'job --help' for help.\n\n"
        "Error: Missing option '--config-files'.\n"
    )


def test_missing_event_name():
    runner = CliRunner()
    result = runner.invoke(job, ["--config-files=engine/config/dev-local.json"])
    assert result.exit_code == 2
    assert (
        result.output == "Usage: job [OPTIONS]\nTry 'job --help' for help.\n\n"
        "Error: Missing option '--event-name'.\n"
    )


def test_empty_config_files():
    runner = CliRunner()
    result = runner.invoke(job, ["--config-files", "--event-name=test.event"])
    assert result.exit_code == 2
    assert (
        result.output
        == "Usage: job [OPTIONS]\nTry 'job --help' for help.\n\nError: Missing option '--event-name'.\n"
    )


def test_job_runs_with_payload_and_tracks(monkeypatch, tmp_path):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text('{"hello": "world"}', encoding="utf-8")

    captured = {}

    async def mock_run_job(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(cli_job, "run_job", mock_run_job)

    runner = CliRunner()
    result = runner.invoke(
        job,
        [
            "--config-files=one.json,two.json",
            "--event-name=app.event",
            f"--payload=@{payload_path}",
            '--track={"foo":"1","track.bar":"two"}',
            '--query-args={"filter":"on","limit":5}',
            "--start-streams",
            "--max-events=5",
        ],
    )

    assert result.exit_code == 0
    assert result.output == Payload.to_json({"ok": True}) + "\n"
    assert captured == {
        "config_files": ["one.json", "two.json"],
        "event_name": "app.event",
        "payload": '{"hello": "world"}',
        "start_streams": True,
        "max_events": 5,
        "track_ids": {"track.foo": "1", "track.bar": "two"},
        "query_args": {"filter": "on", "limit": "5"},
    }


def test_hopeit_job():
    """Test hopeit_job running in a subprocess"""

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    hopeit_proc = None
    proc_output = None

    args = [
        "python",
        "-m",
        "hopeit.cli.job",
        "--config-files=engine/config/dev-noauth.json"
        ",plugins/auth/basic-auth/config/plugin-config.json"
        ",apps/examples/simple-example/config/app-config.json",
        "--event-name=check_enum",
        '--query-args={"enum_value":"value1"}',
    ]

    mock_env = os.environ.copy()
    mock_env["PYTHONPATH"] = (
        "apps/examples/simple-example/src/:plugins/auth/basic-auth/src/:" + mock_env["PYTHONPATH"]
    )

    hopeit_proc = subprocess.Popen(
        args, env=mock_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    proc_output = hopeit_proc.communicate(timeout=15)[0].decode()

    logger.info("\n%s", proc_output)
    assert hopeit_proc.returncode == 0
    assert "ERROR" not in proc_output
    result = json.loads(proc_output.strip().splitlines()[-1])
    assert result == [{"value": "value1"}]
