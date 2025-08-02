from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

APP_VERSION = APPS_API_VERSION.replace(".", "x")


async def test_it_download_something_not_found(app_config):
    file_name = "not_found.png"

    _, pp_result, response = await execute_event(
        app_config=app_config,
        event_name="download_something",
        payload=None,
        postprocess=True,
        file_name=file_name,
    )

    assert pp_result == f"File {file_name} not found"
    assert response.status == 400
