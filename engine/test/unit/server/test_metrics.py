from hopeit.app.context import EventContext
from hopeit.server import metrics

import datetime

from hopeit.server.config import AuthType
from hopeit.server.events import get_event_settings
from hopeit.server.metrics import StreamStats
from mock_app import mock_app_config  # type: ignore  # noqa: F401

ZERO_TS = datetime.datetime.fromtimestamp(0.0).astimezone(datetime.timezone.utc)
ONE_TS = datetime.datetime.fromtimestamp(1.0).astimezone(datetime.timezone.utc)
TWO_TS = datetime.datetime.fromtimestamp(2.0).astimezone(datetime.timezone.utc)


class MockDatetime(datetime.datetime):
    ts = 0.0

    @classmethod
    def now(cls):
        return datetime.datetime.fromtimestamp(cls.ts)


def test_metrics(mock_app_config):  # noqa: F811
    settings = get_event_settings(mock_app_config.effective_settings, 'mock_event')
    context = EventContext(
        app_config=mock_app_config,
        plugin_config=mock_app_config,
        event_name='mock_event',
        settings=settings,
        track_ids={},
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    context.creation_ts = ZERO_TS
    metrics.datetime = MockDatetime
    MockDatetime.ts = 3.0
    result = metrics.metrics(context)
    assert result['extra'] == 'metrics.duration=3000.000'


def test_stream_metrics(mock_app_config):  # noqa: F811
    settings = get_event_settings(mock_app_config.effective_settings, 'mock_event')
    context = EventContext(
        app_config=mock_app_config,
        plugin_config=mock_app_config,
        event_name='mock_event',
        settings=settings,
        track_ids={
            'track.request_ts': ZERO_TS.isoformat()
        },
        auth_info={'auth_type': AuthType.UNSECURED, 'allowed': 'true'}
    )
    context.track_ids['stream.submit_ts'] = ONE_TS.isoformat()
    context.track_ids['stream.read_ts'] = TWO_TS.isoformat()
    context.creation_ts = ZERO_TS
    metrics.datetime = MockDatetime
    MockDatetime.ts = 3.0
    result = metrics.stream_metrics(context)
    assert result['extra'] == 'metrics.stream_age=1000.000 | metrics.request_elapsed=3000.000'


def test_stream_stats(monkeypatch):
    metrics.datetime = MockDatetime
    MockDatetime.ts = 0.0
    stats = StreamStats().ensure_start()
    for i in range(600):
        stats.inc()

    MockDatetime.ts = 60.0
    assert stats.calc() == {
        'avg_error_rate': 0.0,
        'avg_event_duration': 100.0,
        'avg_rate': 10.0,
        'avg_rate_ok_events': 10.0,
        'avg_success': 1.0,
        'consumed_events': 600,
        'elapsed_ms': 60000,
        'error_rate': 0.0,
        'errors': 0,
        'event_duration': 100.0,
        'rate': 10.0,
        'rate_ok_events': 10.0,
        'success_rate': 1.0,
        'total_consumed_events': 600,
        'total_errors': 0,
        'uptime_minutes': 1
    }

    for i in range(540):
        stats.inc()
    for i in range(60):
        stats.inc(error=True)
    MockDatetime.ts = 120
    assert stats.calc() == {
        'avg_error_rate': 0.05,
        'avg_event_duration': 100.0,
        'avg_rate': 10.0,
        'avg_rate_ok_events': 9.5,
        'avg_success': 0.95,
        'consumed_events': 600,
        'elapsed_ms': 60000,
        'error_rate': 0.1,
        'errors': 60,
        'event_duration': 100.0,
        'rate': 10.0,
        'rate_ok_events': 9.0,
        'success_rate': 0.9,
        'total_consumed_events': 1200,
        'total_errors': 60,
        'uptime_minutes': 2
    }
