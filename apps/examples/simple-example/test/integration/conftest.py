from datetime import datetime, timezone

import pytest  # type: ignore
from hopeit.testing.apps import config

from model import Something, User, Status, StatusType, SomethingParams

EVENT_TS = datetime.strptime("2020-05-01T00:00:00", "%Y-%m-%dT%H:%M:%S").astimezone(tz=timezone.utc)


@pytest.fixture
def something_example():
    return Something(id="test", user=User(id="u1", name="test_user"))


@pytest.fixture
def something_upload_example():
    return Something(id="attachment", user=User(id="test", name="test_user"))


@pytest.fixture
def something_params_example():
    return SomethingParams(id="test", user="test_user")


@pytest.fixture
def something_submitted():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=EVENT_TS, type=StatusType.SUBMITTED),
    )


@pytest.fixture
def something_processed():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=EVENT_TS, type=StatusType.PROCESSED),
        history=[Status(ts=EVENT_TS, type=StatusType.SUBMITTED)],
    )


@pytest.fixture
def something_with_status_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=EVENT_TS, type=StatusType.NEW),
    )


@pytest.fixture
def something_with_status_submitted_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=EVENT_TS, type=StatusType.SUBMITTED),
        history=[Status(ts=EVENT_TS, type=StatusType.NEW)],
    )


@pytest.fixture
def something_with_status_processed_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=EVENT_TS, type=StatusType.PROCESSED),
        history=[
            Status(ts=EVENT_TS, type=StatusType.NEW),
            Status(ts=EVENT_TS, type=StatusType.SUBMITTED),
        ],
    )


@pytest.fixture
def app_config():
    return config("apps/examples/simple-example/config/app-config.json")
