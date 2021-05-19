import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import random
import os

import aiohttp

from hopeit.app.context import EventContext
from hopeit.server.names import route_name
from hopeit.dataobjects.jsonify import Json
from hopeit.samsa import Batch, Message, Stats, consume_in_process, get_all_streams, push_in_process
from hopeit.server.serialization import deserialize, serialize


class SamsaClient:

    def __init__(self, *, 
                 push_nodes: List[str], 
                 consume_nodes: List[str],
                 api_version: str,
                 consumer_id: str):
        self.push_nodes = [*push_nodes]
        self.consume_nodes = [*consume_nodes]
        self.all_nodes = sorted(list(set([*push_nodes, *consume_nodes])))
        self.api_version = api_version
        self.consumer_id = consumer_id
        self.push_path = route_name('api', 'samsa', self.api_version, 'push')
        self.consume_path = route_name('api', 'samsa', self.api_version, 'consume')
        self.stas_path = route_name('api', 'samsa', self.api_version, 'stats')
        random.seed(os.getpid())
        random.shuffle(self.consume_nodes)

    async def push(self, batch: Batch, stream_name: str, maxlen: int) -> Dict[str, Dict[str, int]]:
        partitions = defaultdict(list)
        for item in batch.items:
            node_index = hash(item.key) % len(self.push_nodes)
            partitions[self.push_nodes[node_index]].append(item)

        node_res = await asyncio.gather(*[
           self._invoke_push(
               url=url,
               stream_name=stream_name, 
               batch=Batch(items=items), 
               producer_id=self.consumer_id,
               maxlen=maxlen)
            for url, items in partitions.items()
        ])

        return {
            url: res for (url, _), res in zip(partitions.items(), node_res)
        }


    async def consume(self, stream_name: str, consumer_group: str, batch_size: int, timeout_ms: int=1000):
        return await self._invoke_consume(
            url=random.choice(self.consume_nodes),
            stream_name=stream_name,
            consumer_group=consumer_group,
            consumer_id=self.consumer_id,
            batch_size=batch_size,
            timeout_ms=timeout_ms
        )

    async def stats(self, stream_prefix: Optional[str] = None) -> Dict[str, Stats]:
        all_stats = {
            url: node_stats
            for url, node_stats in zip(
                self.all_nodes,
                await asyncio.gather(*[
                    self._invoke_stats(url, stream_prefix)
                    for url in self.all_nodes
                ])
            )
        }
        return all_stats

    async def _invoke_push(self, url: str, stream_name: str, batch: Batch, 
                           producer_id: str, maxlen: int) -> Dict[str, int]:

        if url == "in-process":
            return await push_in_process(
                batch=batch,
                stream_name=stream_name,
                producer_id=producer_id,
                maxlen=maxlen
            )

        async with aiohttp.ClientSession() as client:
            async with client.post(
                url + self.push_path,
                data=Json.to_json(batch),
                params={
                    "stream_name": stream_name,
                    "producer_id": producer_id,
                    "maxlen": maxlen
                }
            ) as res:
                return await res.json()

    async def _invoke_consume(self, url: str, stream_name: str, 
                              consumer_group: str, consumer_id: str,
                              batch_size: int, timeout_ms: int) -> Batch:

        if url == "in-process":
            return await consume_in_process(
                stream_name=stream_name,
                consumer_group=consumer_group,
                consumer_id=consumer_id,
                batch_size=batch_size,
                timeout_ms=timeout_ms
            )

        async with aiohttp.ClientSession() as client:
            async with client.get(
                url + self.consume_path,
                params={
                    "stream_name": stream_name,
                    "consumer_group": consumer_group,
                    "consumer_id": consumer_id,
                    "batch_size": batch_size,
                    "timeout_ms": timeout_ms
                }
            ) as res:
                return Batch.from_dict(await res.json())  # type: ignore

    async def _invoke_stats(self, url: str, stream_prefix: Optional[str]) -> Stats:
        path = url + self.stas_path
        if stream_prefix:
            path += f"?stream_prefix={stream_prefix}"
        async with aiohttp.ClientSession() as client:
            async with client.get(path) as res:
                return Stats.from_dict(await res.json())  # type: ignore
