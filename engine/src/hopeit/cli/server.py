"""
CLI server commands
"""
import sys

try:
    import click
    from hopeit.server import wsgi
except ModuleNotFoundError:
    print("ERROR: Missing dependencies."
          "\n       To use hopeit_server command line tool"
          "\n       install using `pip install hopeit.engine[web,cli]`")
    sys.exit(1)


@click.group()
def server():
    pass


@server.command()
@click.option('--config-files', prompt='Config files',
              help='Comma-separated config file paths, starting with server config, then plugins, then apps.')
@click.option('--api-file', help='Path to openapi complaint json specification.')
@click.option('--host', default='0.0.0.0', help='Server host address or name.')
@click.option('--port', default='8020', help='TCP/IP port to listen.')
@click.option('--path', help='POSIX complaint socket name.')
@click.option('--start-streams', is_flag=True, default=False, help='Auto start reading stream events.')
@click.option('--enabled-groups', default='',
              help="Optional comma-separated group labels to start. If no group is specified, all events will be"
              " started. Events with no group or 'DEFAULT' group label will always be started. 'DEFAULT' group label"
              " can also be used explicitly to start only events with no group or 'DEFAULT' group label.")
@click.option('--workers', default=1, help="Number of workeres to start.")
def run(config_files: str, api_file: str, host: str, port: int, path: str,
        start_streams: bool, enabled_groups: str, workers: int):
    """
    Runs web server hosting apps specified in config files.
    """
    wsgi.run_app(
        host=host,
        port=port,
        config_files=config_files.split(','),
        api_file=api_file,
        start_streams=start_streams,
        enabled_groups=enabled_groups.split(','),
        workers=workers)


cli = click.CommandCollection(sources=[server])

if __name__ == '__main__':
    cli()
