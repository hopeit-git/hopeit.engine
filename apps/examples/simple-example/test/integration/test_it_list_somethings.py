import os
import uuid

import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

from model import Something

APP_VERSION = APPS_API_VERSION.replace('.', "x")


@pytest.fixture
def sample_file_id():
    test_id = str(uuid.uuid4())
    test_id1 = test_id + 'a'
    test_id2 = test_id + 'b'
    json_str1 = '{"id": "' + test_id1 + '", "user": {"id": "u1", "name": "test_user"}, ' \
                + '"status": {"ts": "2020-05-01T00:00:00Z", "type": "NEW"}, "history": []}'
    json_str2 = '{"id": "' + test_id2 + '", "user": {"id": "u1", "name": "test_user"}, ' \
                + '"status": {"ts": "2020-05-01T00:00:00Z", "type": "NEW"}, "history": []}'
    os.makedirs(f'/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/', exist_ok=True)
    with open(f'/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/{test_id1}.json', 'w') as f:
        f.write(json_str1)
        f.flush()
    with open(f'/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/{test_id2}.json', 'w') as f:
        f.write(json_str2)
        f.flush()
    return test_id


@pytest.mark.asyncio
async def test_query_item(app_config, sample_file_id):  # noqa: F811
    results = await execute_event(app_config=app_config,
                                  event_name='list_somethings',
                                  payload=None,
                                  wildcard=f"2020/05/01/00/{sample_file_id}*")
    assert len(results) == 2
    assert all(result.id.startswith(sample_file_id) for result in results)
    assert all(isinstance(result, Something) for result in results)
