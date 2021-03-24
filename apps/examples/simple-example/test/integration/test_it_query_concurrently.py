import os
import uuid

import pytest  # type: ignore

from hopeit.testing.apps import execute_event
from simple_example.collector.query_concurrently import ItemsInfo


@pytest.fixture
def sample_file_ids():
    ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    for test_id in ids:
        json_str = '{"id": "' + test_id + '", "user": {"id": "u1", "name": "test_user"}, ' \
                   + '"status": {"ts": "2020-05-01T00:00:00Z", "type": "NEW"}, "history": []}'
        os.makedirs('/tmp/simple_example.2x0.fs.data_path/', exist_ok=True)
        with open(f'/tmp/simple_example.2x0.fs.data_path/{test_id}.json', 'w') as f:
            f.write(json_str)
            f.flush()
    return ids


@pytest.mark.asyncio
async def test_find_two_items(app_config, sample_file_ids):  # noqa: F811
    payload = ItemsInfo(*sample_file_ids)
    result = await execute_event(app_config=app_config,
                                 event_name='collector.query_concurrently',
                                 payload=payload)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].id == sample_file_ids[0]
    assert result[1].id == sample_file_ids[1]


@pytest.mark.asyncio
async def test_find_one_item(app_config, sample_file_ids):  # noqa: F811
    payload = ItemsInfo(sample_file_ids[0], str(uuid.uuid4()))
    result = await execute_event(app_config=app_config,
                                 event_name='collector.query_concurrently',
                                 payload=payload)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].id == sample_file_ids[0]


@pytest.mark.asyncio
async def test_find_no_items(app_config, sample_file_ids):  # noqa: F811
    payload = ItemsInfo(str(uuid.uuid4()), str(uuid.uuid4()))
    result = await execute_event(app_config=app_config,
                                 event_name='collector.query_concurrently',
                                 payload=payload)
    assert isinstance(result, list)
    assert len(result) == 0
