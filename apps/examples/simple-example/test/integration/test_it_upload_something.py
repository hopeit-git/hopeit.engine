import pytest  # type: ignore

from hopeit.testing.apps import execute_event


@pytest.mark.asyncio
async def test_it_save_something(app_config, something_params_example, something_upload_example):  # noqa: F811

    fields = {
        'id': something_params_example.id, 
        'user': something_params_example.user, 
        'attachment': 'test_file_name.bytes'
    }

    attachments = {
        'attachment': b'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    }

    result = await execute_event(app_config=app_config,
                                event_name='upload_something',
                                payload=None,
                                fields=fields, attachments=attachments,
                                preprocess=True,
                                something_id='test_something_id')

    assert result == [something_upload_example]

    with open('/tmp/simple_example.1x0.upload_something.save_path/attachment-test_file_name.bytes', 'rb') as f:
        data = f.read()
    
    print("data", len(data), data, type(data), len(attachments['attachment']), attachments['attachment'])
    assert data == attachments['attachment']
