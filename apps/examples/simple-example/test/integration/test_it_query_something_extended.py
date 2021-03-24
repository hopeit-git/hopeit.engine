import os
import uuid
from datetime import datetime, timezone

import pytest  # type: ignore

from hopeit.testing.apps import execute_event

from model import Something, SomethingNotFound, Status, StatusType


@pytest.fixture
def sample_file_id():
    test_id = str(uuid.uuid4())
    json_str = '{"id": "' + test_id + '", "user": {"id": "u1", "name": "test_user"}, ' \
               + '"status": {"ts": "2020-05-01T00:00:00Z", "type": "NEW"}, "history": []}'
    os.makedirs('/tmp/simple_example.2x0.fs.data_path/', exist_ok=True)
    with open(f'/tmp/simple_example.2x0.fs.data_path/{test_id}.json', 'w') as f:
        f.write(json_str)
        f.flush()
    return test_id


@pytest.mark.asyncio
async def test_query_item(app_config, sample_file_id):  # noqa: F811
    status = Status(datetime.now(tz=timezone.utc), StatusType.LOADED)
    result, pp_result, res = await execute_event(app_config=app_config,
                                                 event_name='query_something_extended',
                                                 payload=status,
                                                 postprocess=True,
                                                 item_id=sample_file_id)
    assert isinstance(result, Something)
    assert result == pp_result
    assert result.id == sample_file_id
    assert result.status == status


@pytest.mark.asyncio
async def test_query_item_not_found(app_config):  # noqa: F811
    status = Status(datetime.now(tz=timezone.utc), StatusType.LOADED)
    item_id = str(uuid.uuid4())
    result, pp_result, res = await execute_event(app_config=app_config,
                                                 event_name='query_something_extended',
                                                 payload=status,
                                                 postprocess=True,
                                                 item_id=item_id)
    assert res.status == 404
    assert result == pp_result
    assert result == SomethingNotFound(
        path='/tmp/simple_example.2x0.fs.data_path', id=item_id)
