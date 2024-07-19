"""
CLI server commands
"""

import sys
from typing import List

try:
    import click
    from hopeit.server import wsgi
except ModuleNotFoundError:
    print(
        "ERROR: Missing dependencies."
        "\n       To use hopeit_server command line tool"
        "\n       install using `pip install hopeit.engine[web,cli]`"
    )
    sys.exit(1)


@click.group()
def server():
    pass


@server.command()  # type: ignore
@click.option(
    "--config-files",
    required=True,
    help="Comma-separated config file paths, starting with server config, then plugins, then apps.",
)
@click.option("--api-file", default=None, help="Path to openapi complaint json specification.")
@click.option(
    "--api-auto",
    default=None,
    help="When `api_file` is not defined, specify a semicolons-separated"
    " `--api-auto=0.1;Simple Example;Simple Example OpenAPI specs` to define API General Info and"
    " enable the OpenAPI.",
)
@click.option("--host", default="0.0.0.0", help="Server host address or name.")
@click.option("--port", default=8020, help="TCP/IP port to listen.")
@click.option("--path", help="POSIX complaint socket name.")
@click.option(
    "--start-streams",
    is_flag=True,
    default=False,
    help="Auto start reading stream events.",
)
@click.option(
    "--enabled-groups",
    default="",
    help="Optional comma-separated group labels to start. If no group is specified, all events will be"
    " started. Events with no group or 'DEFAULT' group label will always be started. 'DEFAULT' group label"
    " can also be used explicitly to start only events with no group or 'DEFAULT' group label.",
)
@click.option(
    "--workers",
    default=1,
    help="Number of workeres to start. Max number of workers is (cpu_count * 2) + 1",
)
@click.option(
    "--worker-class",
    type=click.Choice(["GunicornWebWorker", "GunicornUVLoopWebWorker"]),
    default="GunicornWebWorker",
    help="Gunicorn aiohttp worker class. Default value is GunicornWebWorker. "
    "GunicornUVLoopWebWorker requires `pip install uvloop`",
)
@click.option(
    "--worker-timeout",
    default=0,
    help="Workers silent for more than this many seconds are killed and "
    "restarted. Value is a positive number or 0. Setting it to 0 has the effect of infinite timeouts "
    "by disabling timeouts for all workers entirely.",
)
def run(
    config_files: str,
    api_file: str,
    host: str,
    port: int,
    path: str,
    start_streams: bool,
    enabled_groups: str,
    workers: int,
    worker_class: str,
    worker_timeout: int,
    api_auto: str,
):
    """
    Runs web server hosting apps specified in config files.
    """
    groups: List[str] = [] if enabled_groups == "" else enabled_groups.split(",")
    files: List[str] = config_files.split(",")
    api_spec = [] if api_auto is None else api_auto.split(";")

    wsgi.run_app(
        host=host,
        port=port,
        path=path,
        config_files=files,
        api_file=api_file,
        api_auto=api_spec,
        start_streams=start_streams,
        enabled_groups=groups,
        workers=workers,
        worker_class=worker_class,
        worker_timeout=worker_timeout,
    )


cli = click.CommandCollection(sources=[server])

if __name__ == "__main__":
    cli()
