import os
import uuid
from datetime import datetime, timezone

import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

from model import Something, SomethingNotFound, Status, StatusType

APP_VERSION = APPS_API_VERSION.replace(".", "x")


@pytest.fixture
def sample_file_id():
    test_id = str(uuid.uuid4())
    json_str = (
        '{"id": "'
        + test_id
        + '", "user": {"id": "u1", "name": "test_user"}, '
        + '"status": {"ts": "2020-05-01T00:00:00Z", "type": "NEW"}, "history": []}'
    )
    os.makedirs(
        f"/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/", exist_ok=True
    )
    with open(
        f"/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/{test_id}.json",
        "w",
    ) as f:
        f.write(json_str)
        f.flush()
    return test_id, "2020/05/01/00"


async def test_query_item(app_config, sample_file_id):  # noqa: F811
    status = Status(datetime.now(tz=timezone.utc), StatusType.LOADED)
    result, pp_result, res = await execute_event(
        app_config=app_config,
        event_name="query_something_extended",
        payload=status,
        postprocess=True,
        item_id=sample_file_id[0],
        partition_key=sample_file_id[1],
    )
    assert isinstance(result, Something)
    assert result == pp_result
    assert result.id == sample_file_id[0]
    assert result.status == status


async def test_query_item_not_found(app_config):  # noqa: F811
    status = Status(datetime.now(tz=timezone.utc), StatusType.LOADED)
    item_id = str(uuid.uuid4())
    result, pp_result, res = await execute_event(
        app_config=app_config,
        event_name="query_something_extended",
        payload=status,
        postprocess=True,
        item_id=item_id,
        partition_key="x",
    )
    assert res.status == 404
    assert result == pp_result
    assert result == SomethingNotFound(
        path=f"/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/x", id=item_id
    )
