import pytest  # type: ignore
from mock_app import mock_app_config  # type: ignore  # noqa: F401
import mock_app.mock_event as mock_event  # type: ignore

from hopeit.server.imports import find_event_handler


def test_find_event_handler(mock_app_config):  # noqa: F811
    impl = find_event_handler(app_config=mock_app_config, event_name='mock_event', event_info=mock_app_config.events['mock_event'])
    assert impl is mock_event


def test_find_event_handler_not_found(mock_app_config):  # noqa: F811
    with pytest.raises(ImportError):
        find_event_handler(app_config=mock_app_config, event_name='unknown')
