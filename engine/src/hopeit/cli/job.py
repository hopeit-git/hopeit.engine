"""
CLI job command
"""

import asyncio

import click

from hopeit.dataobjects.payload import Payload
from hopeit.server.job import parse_track_ids, resolve_payload, run_job
from hopeit.server.logger import engine_logger

engine_logger().init_cli("job")


@click.command()
@click.option(
    "--config-files",
    required=True,
    help="Comma-separated list of server, plugins and app config files.",
)
@click.option("--event-name", required=True, help="Event name to execute.")
@click.option(
    "--payload",
    default=None,
    help="JSON string payload. Use @file or @- for stdin.",
)
@click.option(
    "--input-file",
    default=None,
    help="Read payload from file (same as --payload=@file).",
)
@click.option(
    "--track",
    multiple=True,
    help="Extra track ids (repeatable), format key=value (key can omit 'track.' prefix).",
)
@click.option(
    "--start-streams",
    is_flag=True,
    default=False,
    help="Enable STREAM consumption.",
)
@click.option(
    "--in-process-shuffle",
    is_flag=True,
    default=False,
    help="Execute SHUFFLE stages in-process (no stream consumers).",
)
@click.option(
    "--max-events",
    type=int,
    default=None,
    help="Limit number of consumed events for STREAM runs.",
)
def job(
    config_files: str,
    event_name: str,
    payload: str,
    input_file: str,
    track: tuple[str, ...],
    start_streams: bool,
    in_process_shuffle: bool,
    max_events: int,
):
    """
    Execute a single event as a job.
    """
    payload_str = resolve_payload(payload, input_file)
    track_ids = parse_track_ids(list(track))
    result = asyncio.run(
        run_job(
            config_files=config_files.split(","),
            event_name=event_name,
            payload=payload_str,
            start_streams=start_streams,
            max_events=max_events,
            track_ids=track_ids,
            in_process_shuffle=in_process_shuffle,
        )
    )
    if result is not None:
        click.echo(Payload.to_json(result))


cli = job


if __name__ == "__main__":
    cli()
