import asyncio
import json
import logging

import redis.asyncio as redis
from redis.exceptions import ResponseError

from app.config import settings
from app.db.database import AsyncSessionLocal, init_db
from app.services import cache_service, queue_service
from app.services.embedding_service import embed_text
from app.services.provider_service import get_provider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contextgate.worker")

CONSUMER_NAME = "worker-1"


async def _wait_for_db() -> None:
    """Retry init_db until Postgres is reachable (it may still be booting)."""
    for attempt in range(1, 11):
        try:
            await init_db()
            return
        except Exception as exc:
            logger.warning("Waiting for database (%s/10): %s", attempt, exc)
            await asyncio.sleep(2)
    raise RuntimeError("Database did not become available in time")


async def _ensure_group(client: redis.Redis) -> None:
    """Create the consumer group, ignoring the error if it already exists."""
    try:
        await client.xgroup_create(
            settings.request_stream, settings.consumer_group, id="0", mkstream=True
        )
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _process(payload: dict) -> None:
    request_id = payload["request_id"]
    prompt = payload["prompt"]
    model = payload.get("model") or settings.default_provider

    try:
        provider_name, provider = get_provider(model)
        response_text = await provider.generate(prompt, model)

        embedding = embed_text(prompt)
        async with AsyncSessionLocal() as session:
            await cache_service.store(
                session,
                prompt=prompt,
                response=response_text,
                embedding=embedding,
                provider=provider_name,
                model=model,
                user_id=payload.get("user_id"),
                session_id=payload.get("session_id"),
            )

        await queue_service.publish_result(
            request_id, {"response": response_text, "provider": provider_name}
        )
        logger.info("Processed request %s via provider '%s'", request_id, provider_name)
    except Exception as exc:  # report failures back to the waiting API request
        logger.exception("Failed to process request %s", request_id)
        await queue_service.publish_result(request_id, {"error": str(exc)})


async def _handle_entries(client: redis.Redis, entries: list) -> None:
    """Process a batch of stream entries and ack each one."""
    for message_id, fields in entries:
        payload = json.loads(fields["data"])
        await _process(payload)
        await client.xack(
            settings.request_stream, settings.consumer_group, message_id
        )


async def _reclaim_pending(client: redis.Redis) -> None:
    """Reclaim entries left pending by a previous worker that crashed before ack.

    Basic single-worker recovery: on restart, any still-pending entries are
    orphaned from a prior run, so we claim them with XAUTOCLAIM and re-process
    them (which repopulates the cache for client retries). Advanced retry
    policies (backoff, dead-letter, multi-worker fairness) are out of scope (V2).
    """
    start_id = "0-0"
    try:
        while True:
            result = await client.xautoclaim(
                settings.request_stream,
                settings.consumer_group,
                CONSUMER_NAME,
                min_idle_time=0,
                start_id=start_id,
                count=10,
            )
            # redis-py returns (next_cursor, claimed_entries[, deleted_ids]).
            next_cursor, claimed = result[0], result[1]
            if claimed:
                logger.info(
                    "Reclaiming %d pending request(s) from a previous run",
                    len(claimed),
                )
                await _handle_entries(client, claimed)
            if not claimed or next_cursor == "0-0":
                break
            start_id = next_cursor
    except Exception:
        logger.exception("Failed to reclaim pending stream entries")


async def run() -> None:
    await _wait_for_db()
    client = queue_service.get_redis()
    await _ensure_group(client)
    await _reclaim_pending(client)
    logger.info("Worker listening on stream '%s'", settings.request_stream)

    while True:
        try:
            messages = await client.xreadgroup(
                settings.consumer_group,
                CONSUMER_NAME,
                {settings.request_stream: ">"},
                count=10,
                block=5000,
            )
        except Exception:
            logger.exception("Error reading from stream; retrying")
            await asyncio.sleep(1)
            continue

        if not messages:
            continue

        for _stream, entries in messages:
            await _handle_entries(client, entries)


if __name__ == "__main__":
    asyncio.run(run())
