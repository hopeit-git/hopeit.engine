import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

APP_VERSION = APPS_API_VERSION.replace('.', "x")


@pytest.mark.asyncio
async def test_it_download_something(app_config):

    file_name = "hopeit-iso.png"

    result, pp_result, response = await execute_event(
        app_config=app_config,
        event_name='download_something',
        payload=None,
        postprocess=True,
        file_name=file_name
    )

    assert result.file_name == file_name
    assert pp_result == f"File {file_name}"
    assert response.headers == {
        'Content-Disposition': f'attachment; filename="{file_name}"'
    }
    assert response.file_response == (
        f"/tmp/hopeit/{file_name}"
    )
    assert response.content_type == 'image/png'
