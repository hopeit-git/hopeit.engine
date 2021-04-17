import pytest  # type: ignore

from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_it_download_something(app_config, something_params_example,
                                     something_upload_example):  # noqa: F811

    file_name = "hopeit.png"

    result, _, response = await execute_event(
        app_config=app_config,
        event_name='download_something',
        payload=None,
        postprocess=True,
        file_name=file_name
    )

    ret_header = {'Content-Disposition': f'attachment; filename={file_name}', 'Content-Type': 'image/png'}
    ret_file_response = f"/tmp/simple_example.2x0.fs.data_path/{file_name}"
    ret__ = f"File {file_name}"

    assert response.headers == ret_header
    assert _ == ret__
    assert response.file_response == ret_file_response
    assert result.file_name == file_name