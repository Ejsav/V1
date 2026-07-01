import json

import redis.asyncio as redis

from app.config import settings

_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Lazily create a shared async Redis client."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _result_key(request_id: str) -> str:
    return f"contextgate:result:{request_id}"


async def enqueue_request(payload: dict) -> None:
    """Add a chat request to the Redis stream for the worker to pick up."""
    client = get_redis()
    await client.xadd(settings.request_stream, {"data": json.dumps(payload)})


async def wait_for_result(request_id: str, timeout: int) -> dict | None:
    """Block until the worker publishes a result, or the timeout elapses."""
    client = get_redis()
    popped = await client.blpop(_result_key(request_id), timeout=timeout)
    if popped is None:
        return None
    _key, value = popped
    return json.loads(value)


async def publish_result(request_id: str, result: dict) -> None:
    """Publish a worker result back to the waiting API request."""
    client = get_redis()
    key = _result_key(request_id)
    await client.rpush(key, json.dumps(result))
    await client.expire(key, 60)  # avoid leaking keys if nobody is waiting
