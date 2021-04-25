import asyncio
import sys
from typing import Dict, Iterable, List, Optional, Set, Tuple, Deque
from collections import defaultdict, deque
from base64 import b64decode, b64encode
from functools import partial

from hopeit.dataobjects import dataclass, dataobject
from hopeit.app.config import Compression, Serialization


@dataobject
@dataclass
class Message:
    key: str
    datatype: str
    submit_ts: str
    event_ts: Optional[str]
    track_ids: Dict[str, str]
    auth_info: str
    ser: Serialization
    comp: Compression
    b64value: Optional[str] = None

    def encode(self, payload: bytes) -> "Message":
        self.b64value = b64encode(payload).decode()
        return self

    @property
    def payload(self) -> bytes:
        return b64decode(self.b64value.encode())  # type: ignore


@dataobject
@dataclass
class Batch:
    items: List[Message]
    missed: int = 0


@dataobject
@dataclass
class ConsumerGroupStats:
    consumers: Dict[str, int]
    next_offset: int
    missed: int
    lag: int


@dataobject
@dataclass
class StreamStats:
    producers: Dict[str, int]
    head_offset: int
    maxlen: int
    currlen: int
    consumer_groups: Dict[str, ConsumerGroupStats]


@dataobject
@dataclass
class Stats:
    host: str
    streams: Dict[str, StreamStats]


class Queue:
    def __init__(self, maxlen: int):
        self.maxlen = maxlen or 1024
        self.data: Deque[Optional[Message]] = deque(
            iterable=[None] * self.maxlen, maxlen=self.maxlen if self.maxlen else None
        )
        self.producer_ids: Dict[str, int] = defaultdict(int)
        self.consumer_offsets: Dict[str, int] = defaultdict(int)
        self.consumer_ids: Dict[str, Dict[str, int]] = defaultdict(self._consumer_ids_item_factory)
        self.offset0 = -1
        self._lock = asyncio.Lock()

    @staticmethod
    def _consumer_ids_item_factory() -> Dict[str, int]:
        return defaultdict(int)


    def __repr__(self):
        return (
            f"consumer_offsets={dict(self.consumer_offsets.items())} \n"
            f"offset0={self.offset0} \n"
        )

    async def push(self, items: List[Message], producer_id: str) -> int:
        async with self._lock:
            self.data.extendleft(items)
            self.offset0 += len(items)
            self.producer_ids[producer_id] += len(items)
            return self.offset0

    async def consume(self, consumer_group: str, consumer_id: str, batch_size: int) -> Tuple[List[Message], int]:
        async with self._lock:
            items: List[Message] = []
            index = self.offset0 - self.consumer_offsets[consumer_group]
            missed = max(0, index - self.maxlen + 1)
            if missed > 0:
                index -= missed

            item = self.data[index]
            while (index >= 0) and (item is not None) and (len(items) < batch_size):
                items.append(self.data[index])  # type: ignore
                index -= 1

            self.consumer_offsets[consumer_group] = self.consumer_offsets[consumer_group] + len(items) + missed
            self.consumer_ids[consumer_group][consumer_id] += len(items)
            return items, missed

    def stats(self) -> StreamStats:
        return StreamStats(
            producers=self.producer_ids,
            head_offset=self.offset0,
            maxlen=self.maxlen,
            currlen=len(self.data),
            consumer_groups={
                consumer_group: ConsumerGroupStats(
                    consumers=self.consumer_ids[consumer_group],
                    next_offset=offset,
                    missed=max(0, self.offset0 - offset - self.maxlen + 1),
                    lag=self.offset0 - offset + 1
                ) for consumer_group, offset in self.consumer_offsets.items()
            }
        )


_queues: Dict[str, Queue] = {}
_queues_lock = asyncio.Lock()


async def ensure_stream(stream_name: str, maxlen: int) -> Queue:
    global _queues
    async with _queues_lock:
        q = _queues.get(stream_name)
        if q is None:
            q = Queue(maxlen=maxlen)
            _queues[stream_name] = q
    return q


def get_stream(stream_name: str) -> Optional[Queue]:
    return _queues.get(stream_name)


def get_all_streams() -> Iterable[Tuple[str, Queue]]:
    return _queues.items()


async def push_in_process(batch: Batch, stream_name: str, producer_id: str, maxlen: int):
    q = await ensure_stream(stream_name=stream_name, maxlen=maxlen)
    return await q.push(batch.items, producer_id=producer_id)


async def consume_in_process(stream_name: str, consumer_group: str, consumer_id: str,
                             batch_size: int, timeout_ms: int) -> Batch:
    q = get_stream(stream_name)
    if q is None:
        return Batch(items=[], missed=0)

    for _ in range(2):
        items, missed = await q.consume(consumer_group, consumer_id, batch_size)
        if len(items) > 0:
            break
        await asyncio.sleep(timeout_ms / 1000.0)

    return Batch(items=items, missed=missed)
