"""
Collect Event Stats from log stream
"""
from typing import Deque, Dict, Set, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from hopeit.app.context import EventContext
from hopeit.dataobjects import dataclass, dataobject
from hopeit.server.names import auto_path

from hopeit.log_streamer import LogBatch, LogEntry


@dataobject
@dataclass
class EventStats:
    started: int = 0
    done: int = 0
    failed: int = 0
    recent: int = 0

    @property
    def pending(self):
        return max(0, self.started - self.done - self.failed)


recent_entries: Deque[LogEntry] = deque(maxlen=2000)

__steps__ = ['consume']


async def consume(batch: LogBatch, context: EventContext) -> None:
    recent_entries.extend(batch.entries)


def get_stats(host_pids: Set[Tuple[str, str]], time_window_secs: int, recent_secs: int) -> Dict[str, EventStats]:
    """
    Collect node event stats, counting for each node with recent entries
    number of started, done, pending and failed events.

    :param: host_pids, str tuple, set of host-pid pairs to filter log entries
    :param: time_window_secs: int, consider events not older than this
    :param: recent_secs: int, events on the last seconds will be counted as recent
    """
    stats: Dict[str, EventStats] = defaultdict(EventStats)
    now_ts = datetime.now(tz=timezone.utc)
    from_ts = (now_ts - timedelta(seconds=time_window_secs)).strftime("%Y-%m-%d %H:%M:%S")
    recent_ts = (now_ts - timedelta(seconds=recent_secs)).strftime("%Y-%m-%d %H:%M:%S")
    for entry in recent_entries:
        if entry.ts >= from_ts and (entry.host, entry.pid) in host_pids:
            event_name = entry.extra.get("stream.event_name", entry.event_name)
            event_name = f"{auto_path(entry.app_name, entry.app_version)}.{event_name}"
            event_stats = stats[event_name]
            stream_key = ">" + entry.extra.get("stream.name", "NA")
            stream_queue = "." + entry.extra.get("stream.queue", "")
            if stream_key[-len(stream_queue):] == stream_queue:
                stream_key = stream_key[0:-len(stream_queue)]
            stream_stats = stats[stream_key]
            stream_key = (stream_key + stream_queue).strip('.')
            stats[stream_key] = stream_stats
            if entry.msg == "START":
                event_stats.started += 1
                stream_stats.started += 1
            elif entry.msg == "DONE":
                event_stats.done += 1
                stream_stats.done += 1
            elif entry.msg == "FAILED":
                event_stats.failed += 1
                stream_stats.failed += 1
            if entry.ts >= recent_ts:
                event_stats.recent += 1
                stream_stats.recent += 1
    return stats
