from __future__ import annotations

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.core.config import get_settings


_settings = get_settings()
redis_client: Redis = aioredis.from_url(
    _settings.REDIS_URL,
    decode_responses=True,
)


def get_redis_client() -> Redis:
    return redis_client


async def close_redis_client() -> None:
    await redis_client.aclose()
