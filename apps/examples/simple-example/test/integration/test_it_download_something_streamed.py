import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

APP_VERSION = APPS_API_VERSION.replace('.', "x")


@pytest.mark.asyncio
async def test_it_download_something_streamed(app_config):

    file_name = "hopeit-iso.png"

    result, pp_result, response = await execute_event(
        app_config=app_config,
        event_name='download_something_streamed',
        payload=None,
        postprocess=True,
        file_name=file_name
    )

    assert result.file_name == file_name
    assert pp_result.file_name == file_name
    assert response.headers == {
        'Content-Disposition': f'attachment; filename={file_name}'
    }
    assert response.stream_response.resp == (
        f"/tmp/simple_example.{APP_VERSION}.fs.data_path/{file_name}"
    )
    assert response.content_type == 'image/png'
