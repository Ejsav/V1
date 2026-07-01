from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import SemanticCache


@dataclass
class CacheMatch:
    response: str
    provider: str
    similarity: float


async def find_similar(
    session: AsyncSession, embedding: list[float]
) -> CacheMatch | None:
    """Return the closest cached response if it clears the similarity threshold."""
    distance = SemanticCache.embedding.cosine_distance(embedding)
    stmt = (
        select(SemanticCache, distance.label("distance"))
        .order_by(distance)
        .limit(1)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        return None

    record, dist = row
    similarity = 1.0 - float(dist)  # cosine distance -> cosine similarity
    if similarity < settings.cache_similarity_threshold:
        return None

    return CacheMatch(
        response=record.response,
        provider=record.provider,
        similarity=round(similarity, 4),
    )


async def store(
    session: AsyncSession,
    *,
    prompt: str,
    response: str,
    embedding: list[float],
    provider: str,
    model: str,
    user_id: str | None,
    session_id: str | None,
) -> None:
    """Persist a new prompt/response pair into the semantic cache."""
    session.add(
        SemanticCache(
            prompt=prompt,
            response=response,
            embedding=embedding,
            provider=provider,
            model=model,
            user_id=user_id,
            session_id=session_id,
        )
    )
    await session.commit()
