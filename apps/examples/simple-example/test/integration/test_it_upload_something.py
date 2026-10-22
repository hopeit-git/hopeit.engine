import pytest

from hopeit.server.version import APPS_API_VERSION
from hopeit.testing.apps import execute_event

APP_VERSION = APPS_API_VERSION.replace(".", "x")


async def test_it_save_something(app_config, something_params_example, something_upload_example):
    fields = {
        "id": something_params_example.id,
        "user": something_params_example.user,
        "attachment": "test_file_name.bytes",
        "object": {"id": "test", "user": {"id": "test", "name": "test_user"}},
    }

    upload = {"attachment": b"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}

    result = await execute_event(
        app_config=app_config,
        event_name="upload_something",
        payload=None,
        fields=fields,
        upload=upload,
        preprocess=True,
        something_id="test_something_id",
    )

    assert result == [something_upload_example]

    with open(  # noqa: ASYNC230 -- Small synchronous test fixture with controlled file lifetime.
        f"/tmp/hopeit/simple_example.{APP_VERSION}.upload_something.save_path/attachment-test_file_name.bytes",
        "rb",
    ) as f:
        data = f.read()

    assert data == upload["attachment"]


async def test_it_save_something_missing_field(
    app_config, something_params_example, something_upload_example
):
    fields = {
        "id": something_params_example.id,
        "user": something_params_example.user,
        "object": {"id": "test", "user": {"id": "test", "name": "test_user"}},
    }

    result, _, response = await execute_event(
        app_config=app_config,
        event_name="upload_something",
        payload=None,
        fields=fields,
        preprocess=True,
        postprocess=True,
        something_id="test_something_id",
    )

    assert result == "Missing required fields"
    assert response.status == 400


@pytest.mark.parametrize("object_field", ["invalid JSON", {"id": "test", "user": "invalid"}])
async def test_it_save_something_invalid_object(app_config, object_field):
    result, _, response = await execute_event(
        app_config=app_config,
        event_name="upload_something",
        payload=None,
        fields={"id": "test", "user": "test", "attachment": "test.txt", "object": object_field},
        upload={"attachment": b"test content"},
        preprocess=True,
        postprocess=True,
        something_id="test_something_id",
    )
    assert result == "Invalid object field"
    assert response.status == 400
