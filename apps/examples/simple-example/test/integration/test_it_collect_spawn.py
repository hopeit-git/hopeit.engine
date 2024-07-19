import os
import uuid

import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from hopeit.server.version import APPS_API_VERSION

from model import Something
from simple_example.collector.collect_spawn import ItemsInfo, ItemsCollected

APP_VERSION = APPS_API_VERSION.replace('.', "x")


def test_fail():
    assert False


@pytest.fixture
def sample_file_ids():
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    for test_id in ids:
        json_str = '{"id": "' + test_id + '", "user": {"id": "u1", "name": "test_user"}, ' \
                   + '"status": {"ts": "2020-05-01T00:00:00Z", "type": "NEW"}, "history": []}'
        os.makedirs(f'/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/', exist_ok=True)
        with open(f'/tmp/hopeit/simple_example.{APP_VERSION}.fs_storage.path/2020/05/01/00/{test_id}.json', 'w') as f:
            f.write(json_str)
            f.flush()
    return ids


@pytest.mark.asyncio
async def test_find_two_items(app_config, sample_file_ids):  # noqa: F811
    payload = ItemsInfo(*sample_file_ids)
    payload.partition_key = "2020/05/01/00/"
    result, pp_result, response = await execute_event(app_config=app_config,
                                                      event_name='collector.collect_spawn',
                                                      payload=payload,
                                                      postprocess=True)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].id == sample_file_ids[0]
    assert result[1].id == sample_file_ids[1]
    assert pp_result == 2


@pytest.mark.asyncio
async def test_find_one_item(app_config, sample_file_ids):  # noqa: F811
    payload = ItemsInfo(sample_file_ids[0], str(uuid.uuid4()))
    payload.partition_key = "2020/05/01/00/"
    result, pp_result, response = await execute_event(app_config=app_config,
                                                      event_name='collector.collect_spawn',
                                                      payload=payload,
                                                      postprocess=True)
    assert isinstance(result, Something)
    assert result.id == sample_file_ids[0]
    assert pp_result == 1


@pytest.mark.asyncio
async def test_find_no_items(app_config, sample_file_ids):  # noqa: F811
    payload = ItemsInfo(str(uuid.uuid4()), str(uuid.uuid4()))
    result, pp_result, response = await execute_event(app_config=app_config,
                                                      event_name='collector.collect_spawn',
                                                      payload=payload,
                                                      postprocess=True)
    assert result == ItemsCollected([])
    assert pp_result == 0
