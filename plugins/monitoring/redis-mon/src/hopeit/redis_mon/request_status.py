from typing import Optional

import aioredis
from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger

from hopeit.redis_mon import RequestStats

logger, extra = app_extra_logger()

__steps__ = ['query_status']

__api__ = event_api(
    query_args=[('request_id', str, 'track.request_id')],
    responses={
        200: (RequestStats, "Stats about request processed events")
    }
)

redis: Optional[aioredis.Redis] = None

async def __init_event__(context: EventContext):
    global redis
    logger.info(context, "Connecting monitoring plugin...")
    redis = await aioredis.create_redis('redis://localhost:6379')


async def _get_int(key):
    v = await redis.get(key)
    if v is None:
        return 0
    return int(v.decode())


async def query_status(payload: None, context: EventContext, request_id: str) -> RequestStats:
    assert redis, "No hay redis"
    try:
        return RequestStats(
            request_id=request_id,
            total=await _get_int(f'{request_id}_START'),
            done=await _get_int(f'{request_id}_DONE'),
            failed=await _get_int(f'{request_id}_FAILED')
        )
    except Exception as e:
        print(e)
