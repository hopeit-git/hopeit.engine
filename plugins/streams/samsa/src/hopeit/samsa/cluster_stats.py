from typing import Dict, List, Optional

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataobjects import dataobject, dataclass

from hopeit.samsa import Stats
from hopeit.samsa.client import SamsaClient

logger, extra = app_extra_logger()

__steps__ = ['stats']


@dataobject
@dataclass
class ClusterStats:
    nodes: Dict[str, Stats]


async def stats(payload: None, context: EventContext,
                *, nodes: str, stream_prefix: Optional[str] = None) -> ClusterStats:
    print("***************", context.app.name, context.app.version)
    client = SamsaClient(
        push_nodes=[], 
        consume_nodes=nodes.split(','),
        api_version=context.app.version,
        consumer_id=f"{context.app_key}.{context.event_name}"
    )
    return ClusterStats(nodes=await client.stats(stream_prefix))
