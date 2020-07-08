from datetime import datetime

import pytest  # type: ignore
from hopeit.testing.apps import config

from model import Something, User, Status, StatusType, SomethingParams


@pytest.fixture
def something_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user")
    )


@pytest.fixture
def something_params_example():
    return SomethingParams(id='test', user='test_user')


@pytest.fixture
def something_submitted():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=datetime.now(), type=StatusType.SUBMITTED)
    )


@pytest.fixture
def something_processed():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=datetime.now(), type=StatusType.PROCESSED),
        history=[Status(ts=datetime.now(), type=StatusType.SUBMITTED)]
    )


@pytest.fixture
def something_with_status_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=datetime.now(), type=StatusType.NEW)
    )


@pytest.fixture
def something_with_status_submitted_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=datetime.now(), type=StatusType.SUBMITTED),
        history=[Status(ts=datetime.now(), type=StatusType.NEW)]
    )


@pytest.fixture
def something_with_status_processed_example():
    return Something(
        id="test",
        user=User(id="u1", name="test_user"),
        status=Status(ts=datetime.now(), type=StatusType.PROCESSED),
        history=[Status(ts=datetime.now(), type=StatusType.NEW),
                 Status(ts=datetime.now(), type=StatusType.SUBMITTED)]
    )


@pytest.fixture
def app_config():
    return config('apps/examples/simple-example/config/1x0.json')
