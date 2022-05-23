"""
CLI server commands
"""
import sys

try:
    import click
    from hopeit.server import web
except ModuleNotFoundError:
    print("ERROR: Missing dependencies."
          "\n       To use hopeit_server command line tool"
          "\n       install using `pip install hopeit.engine[web,cli]`")
    sys.exit(1)


@click.group()
def server():
    pass


@server.command()
@click.option('--config-files', prompt='Config files.',
              help='Comma-separated config file paths, starting with server config, then plugins, then apps.')
@click.option('--api-file', help='Path to openapi complaint json specification.')
@click.option('--host', default='0.0.0.0', help='Server host address or name.')
@click.option('--port', default='8020', help='TCP/IP port to listen.')
@click.option('--path', help='POSIX complaint socket name.')
@click.option('--start-streams', is_flag=True, default=False, help='Auto start reading stream events.')
@click.option('--groups', prompt='Comma-separated group label.',
              help="List of groups to start. When no group is specified, all envents will start."
                   "You can add 'DEFAULT' group label to start events without explicit groups setting")
def run(config_files: str, api_file: str, host: str, port: int, path: str, start_streams: bool, groups: str):
    """
    Runs web server hosting apps specified in config files.
    """
    web.prepare_engine(
        config_files=config_files.split(','), api_file=api_file, start_streams=start_streams, groups=groups.split(',')
    )
    web.serve(host=host, path=path, port=port)


cli = click.CommandCollection(sources=[server])

if __name__ == '__main__':
    cli()
