"""
Metrics module
"""
from datetime import datetime, timezone
from typing import Dict, Union, Optional

from hopeit.server.logger import format_extra_values
from hopeit.app.context import EventContext


__all__ = ['metrics',
           'stream_metrics',
           'StreamStats']


def metrics(context: EventContext):
    """
    Return event calculated metrics using EventContext as a dictionary that can be used
    in logging

    :param context: EventContext
    return: dictionary than can be passed to logging extra= parameter
    """
    return {'extra': format_extra_values(
        _calc_event_metrics(context),
        prefix='metrics.'
    )}


def stream_metrics(context: EventContext):
    """
    Return stream event calculated metrics using EventContext as a dictionary that can be used
    in logging

    :param context: EventContext
    :return: dictionary than can be passed to logging extra= parameter
    """
    return {'extra': format_extra_values(
        _calc_stream_metrics(context),
        prefix='metrics.'
    )}


def _calc_event_metrics(context: EventContext):
    duration = 1000.0 * (
        datetime.now().astimezone(tz=timezone.utc) - context.creation_ts
    ).total_seconds()
    return {
        'duration': f"{duration:.3f}"
    }


def _calc_stream_metrics(context: EventContext):
    """
    Calculates stream events standard metrics:

    stream_age: difference between read_ts and submit_ts indicating time that event
        spent unconsumed
    event_elapsed: difference between now and event request_ts indicating time elapsed
        since event request was first created even before published to a stream
    :param: context, EventContext
    :return: dictionary than can be passed to logging extra= parameter
    """
    result = {}
    submit_ts = context.track_ids.get("stream.submit_ts")
    read_ts = context.track_ids.get("stream.read_ts")
    if submit_ts and read_ts:
        submit_dt = datetime.fromisoformat(submit_ts)
        read_dt = datetime.fromisoformat(read_ts)
        age = 1000.0 * (read_dt - submit_dt).total_seconds()
        result['stream_age'] = f"{age:.3f}"
    request_ts = context.track_ids.get("track.request_ts")
    if request_ts:
        request_dt = datetime.fromisoformat(request_ts)
        elapsed = 1000.0 * (
            datetime.now().astimezone(timezone.utc) - request_dt
        ).total_seconds()
        result['request_elapsed'] = f"{elapsed:.3f}"
    return result


class StreamStats:
    """
    Helper class to keep stream consuming stats
    """
    def __init__(self):
        self.run_ts: datetime = datetime.now()
        self.start_ts: Optional[datetime] = None
        self.from_ts: Optional[datetime] = None
        self.event_count: int = 0
        self.error_count: int = 0
        self.total_event_count = 0
        self.total_error_count: int = 0

    def ensure_start(self):
        if self.start_ts is None:
            self.start_ts = datetime.now()
            self.from_ts = datetime.now()
            self.event_count: int = 0
            self.error_count: int = 0
            self.total_event_count = 0
            self.total_error_count: int = 0
        return self

    def reset_batch(self, now: datetime):
        self.from_ts = now
        self.event_count = 0
        self.error_count = 0

    def inc(self, error: bool = False):
        self.event_count += 1
        self.total_event_count += 1
        if error:
            self.error_count += 1
            self.total_error_count += 1

    def calc(self) -> Dict[str, Union[int, float]]:
        """
        calculate stream stats to be logged
        :return: dict, with stream stats to be used as extra info for logging
        """
        assert self.start_ts is not None and self.from_ts is not None, \
            "StreamStats not initialized. Call `ensure_start()`"
        now = datetime.now()
        total_elapsed_td = now - self.start_ts
        total_elapsed = 1000.0 * total_elapsed_td.total_seconds()
        avg_rate = (1000.0 * self.total_event_count / total_elapsed) if total_elapsed else 0.0
        avg_rate_success = (1000.0 * (self.total_event_count - self.total_error_count) / total_elapsed) \
            if total_elapsed else 0.0
        avg_duration = (1.0 * total_elapsed / self.total_event_count) if self.total_event_count else 0.0
        partial_elapsed_td = now - self.from_ts
        partial_elapsed = 1000.0 * partial_elapsed_td.total_seconds()
        rate = (1000.0 * self.event_count / partial_elapsed) if partial_elapsed else 0.0
        rate_success = (1000.0 * (self.event_count - self.error_count) / partial_elapsed) \
            if partial_elapsed else 0.0
        duration = (1.0 * partial_elapsed / self.event_count) if self.event_count else 0.0
        error_rate = (1.0 * self.total_error_count / self.total_event_count) if self.total_event_count else 0.0
        success = 1.0 - error_rate
        partial_error_rate = (1.0 * self.error_count / self.event_count) if self.event_count else 0.0
        partial_success = 1.0 - partial_error_rate
        uptime_elapsed_td = now - self.run_ts
        uptime_elapsed = 1000.0 * uptime_elapsed_td.total_seconds()
        uptime = int(uptime_elapsed / 60000)
        stats = {
            'total_consumed_events': self.total_event_count,
            'total_errors': self.total_error_count,
            'avg_rate': avg_rate,
            'avg_event_duration': avg_duration,
            'avg_rate_ok_events': avg_rate_success,
            'avg_success': success,
            'avg_error_rate': error_rate,
            'elapsed_ms': int(partial_elapsed),
            'consumed_events': self.event_count,
            'errors': self.error_count,
            'rate': rate,
            'event_duration': duration,
            'rate_ok_events': rate_success,
            'uptime_minutes': uptime,
            'success_rate': partial_success,
            'error_rate': partial_error_rate
        }
        self.reset_batch(now)
        return stats
