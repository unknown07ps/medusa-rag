import hashlib
import json
from typing import Optional

import redis.asyncio as aioredis
import structlog

from app.core.config import settings
from app.monitoring.metrics import CACHE_HIT_COUNT

logger = structlog.get_logger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _cache_key(query: str, prompt_version: str) -> str:
    digest = hashlib.sha256(f"{prompt_version}:{query}".encode()).hexdigest()
    return f"medusa:query:{digest}"


async def get_cached_response(query: str, prompt_version: str) -> Optional[dict]:
    try:
        r = await get_redis()
        key = _cache_key(query, prompt_version)
        raw = await r.get(key)
        if raw:
            CACHE_HIT_COUNT.labels(result="hit").inc()
            return json.loads(raw)
        CACHE_HIT_COUNT.labels(result="miss").inc()
        return None
    except Exception as exc:
        logger.warning("Cache get failed", error=str(exc))
        CACHE_HIT_COUNT.labels(result="miss").inc()
        return None


async def set_cached_response(query: str, prompt_version: str, response: dict) -> None:
    try:
        r = await get_redis()
        key = _cache_key(query, prompt_version)
        payload = {k: v for k, v in response.items() if k != "tracer"}
        await r.set(key, json.dumps(payload), ex=settings.CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Cache set failed", error=str(exc))
