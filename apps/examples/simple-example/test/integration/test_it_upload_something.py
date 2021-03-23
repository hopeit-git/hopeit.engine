import pytest  # type: ignore

from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_it_save_something(app_config, something_params_example, something_upload_example):  # noqa: F811

    fields = {
        'id': something_params_example.id,
        'user': something_params_example.user,
        'attachment': 'test_file_name.bytes',
        'object': {"id": "test", "user": {"id": "test", "name": "test_user"}}
    }

    upload = {
        'attachment': b'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    }

    result = await execute_event(app_config=app_config,
                                 event_name='upload_something',
                                 payload=None,
                                 fields=fields, upload=upload,
                                 preprocess=True,
                                 something_id='test_something_id')

    assert result == [something_upload_example]

    with open('/tmp/simple_example.1x0.upload_something.save_path/attachment-test_file_name.bytes', 'rb') as f:
        data = f.read()

    print("data", len(data), data, type(data), len(upload['attachment']), upload['attachment'])
    assert data == upload['attachment']


@pytest.mark.asyncio
async def test_it_save_something_missing_field(app_config, something_params_example,
                                               something_upload_example):  # noqa: F811

    fields = {
        'id': something_params_example.id,
        'user': something_params_example.user,
        'object': {"id": "test", "user": {"id": "test", "name": "test_user"}}
    }

    result, _, response = await execute_event(
        app_config=app_config,
        event_name='upload_something',
        payload=None,
        fields=fields,
        preprocess=True,
        postprocess=True,
        something_id='test_something_id'
    )

    assert result == "Missing required fields"
    print(response)
    assert response.status == 400
