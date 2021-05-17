"""
CLI openapi commands
"""
import sys
import re

try:
    import click
    from deepdiff import DeepDiff  # type: ignore

    from hopeit.app.config import parse_app_config_json
    from hopeit.server import api
    from hopeit.server.config import parse_server_config_json
    from hopeit.server.logger import engine_logger
except ModuleNotFoundError:
    print("ERROR: Missing dependencies."
          "\n       To use hopeit_server command line tool"
          "\n       install using `pip install hopeit.engine[web,cli]`")
    sys.exit(1)

logger = engine_logger().init_cli('openapi')
setattr(api, 'logger', logger)


@click.group()
def openapi():
    pass


@openapi.command()
@click.option('--api-version', prompt='API Version', help='API Version string x.x.x.')
@click.option('--title', prompt='API Title', help='API title string.')
@click.option('--description', prompt='API Description', help='API description string.')
@click.option('--config-files', help='Comma-separated list of server, plugins and app config files.')
@click.option('--output-file', help='Path to json api file to be loaded.')
@click.option('--generate', is_flag=True, default=False, help='Indicates to generate paths for all events.')
def create(api_version: str, title: str, description: str, config_files: str,
           output_file: str, generate: bool):
    """
    Creates OpenAPI spec file
    """
    logger.info(__name__, "openapi.update")
    if generate:
        api.setup(generate_mode=True)
    api.init_empty_spec(api_version, title, description)
    _update_api_spec(config_files)
    api.static_spec = api.spec
    api.save_api_file(output_file, api_version)


@openapi.command()
@click.option('--api-version',
              help='API Version string x.x.x. Needs to be incremented if there are spec changes during update.')
@click.option('--config-files', help='Comma-separated list of server, plugins and app config files.')
@click.option('--input-file', help='Path to json api file to be loaded.')
@click.option('--output-file', help='Path to json api file to be loaded.')
@click.option('--generate', is_flag=True, default=False, help='Indicates to generate paths for all events.')
def update(api_version: str, config_files: str, input_file: str, output_file: str, generate: bool = False):
    """
    Updates OpenAPI spec based on current input file plus running configuration from apps.
    """
    logger.info(__name__, "openapi.update")
    if generate:
        api.setup(generate_mode=True)
    api.load_api_file(input_file)
    _update_api_spec(config_files)
    api.save_api_file(output_file, api_version)


@openapi.command()
@click.option('--config-files', help='Comma-separated list of plugins and app config files.')
@click.option('--input-file', help='Path to json api file to be loaded.')
@click.option('--generate', is_flag=True, help='Indicates to generate paths for all events.')
def diff(config_files: str, input_file: str, generate: bool):
    """
    List differences between input OpenAPI spec file and computed API from apps.
    """
    logger.info(__name__, "openapi.diff")
    if generate:
        api.setup(generate_mode=True)
    api.load_api_file(input_file)
    _update_api_spec(config_files)
    ddiff = DeepDiff(api.static_spec, api.spec, ignore_order=True)
    if len(ddiff) > 0:
        logger.warning(__name__, "Running configuration differs from API spec. Check differences.")
        for reason, items in ddiff.items():
            print()
            print(reason)
            for item in items:
                print('\t', item)
                try:
                    old_value = str(eval(item, None, {'root': api.static_spec}))  # pylint: disable=eval-used
                except Exception as e:  # pylint: disable=broad-except
                    old_value = str(e)
                try:
                    new_value = str(eval(item, None, {'root': api.spec}))  # pylint: disable=eval-used
                except Exception as e:  # pylint: disable=broad-except
                    new_value = str(e)
                print('\t\t<<<', re.sub('\n', ' ', old_value))
                print('\t\t>>>', re.sub('\n', ' ', new_value))
    else:
        logger.info(__name__, "OK: API spec and running configuration match.")


def _update_api_spec(config_files: str):
    """
    Computes and updates api module OpenAPI spec from specified config files argument.
    """
    apps_config = []
    config_files_list = config_files.split(',')
    with open(config_files_list[0], 'r') as sf:
        server_config = parse_server_config_json(sf.read())
        api.register_server_config(server_config)
    for path in config_files_list[1:]:
        with open(path, 'r') as f:
            app_config = parse_app_config_json(f.read())
            apps_config.append(app_config)
    api.register_apps(apps_config)


cli = click.CommandCollection(sources=[openapi])


if __name__ == '__main__':
    cli()
