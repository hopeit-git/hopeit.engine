from datetime import datetime, timezone
import os
import socket
from typing import List, Optional

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.streams import StreamManager

from hopeit.samsa import Stats, get_all_streams

logger, extra = app_extra_logger()

__steps__ = ['stats']


def _host() -> str:
    ts = datetime.now().astimezone(tz=timezone.utc).isoformat()
    host = socket.gethostname()
    pid = os.getpid()
    return f"{ts}.{host}.{pid}"


HOST = _host()


async def stats(payload: None, context: EventContext, stream_prefix: Optional[str] = None) -> Stats:
    streams = get_all_streams()
    if stream_prefix:
        streams = [
            (k, v) for k, v in streams
            if (k[0:len(stream_prefix)] == stream_prefix)
        ]
    return Stats(
        host=HOST,
        streams={
            stream_name: q.stats()
            for stream_name, q in streams
        }
    )
