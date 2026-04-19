import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


# ── TTL Constants ─────────────────────────────────────────────────────────────
TTL_MODEL_META = 60       # active model metadata
TTL_USER_PROFILE = 300    # JWT resolution cache
TTL_JOB_STATUS = 2        # job polling cache


async def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        logger.warning("cache_set_failed", key=key)


async def cache_get(key: str) -> Any | None:
    try:
        r = await get_redis()
        raw = await r.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception:
        logger.warning("cache_get_failed", key=key)
        return None


async def cache_delete(key: str) -> None:
    try:
        r = await get_redis()
        await r.delete(key)
    except Exception:
        logger.warning("cache_delete_failed", key=key)


# ── Typed Cache Helpers ───────────────────────────────────────────────────────

def model_meta_key() -> str:
    return "model:active:meta"


def user_profile_key(user_id: str) -> str:
    return f"user:{user_id}:profile"


def job_status_key(job_id: str) -> str:
    return f"job:{job_id}:status"


async def invalidate_model_cache() -> None:
    await cache_delete(model_meta_key())


async def invalidate_job_cache(job_id: str) -> None:
    await cache_delete(job_status_key(job_id))
