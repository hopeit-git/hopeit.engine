from datetime import datetime, timezone
import uuid
import pytest  # type: ignore

from hopeit.testing.apps import config

from . import MyObject


@pytest.fixture
def test_objs():
    # Creates 10 elements, in 5 partitions
    return [
        MyObject(
            object_id=f"obj{i}",
            object_ts=datetime.strptime(
                f"2020-05-01T0{i//2}:00:00+00:00", "%Y-%m-%dT%H:%M:%S%z"
            ).astimezone(tz=timezone.utc),
            value=i
        ) for i in range(10)
    ]


@pytest.fixture
def app_config():
    cfg = config("plugins/storage/fs/test/integration/app_config.json")
    # Set unique folder for each test run
    cfg.settings["test_stream_batch_storage"]["path"] += f"/{str(uuid.uuid4())}"
    return cfg
