import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_session
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import cache_service, queue_service
from app.services.embedding_service import embed_text

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    request_id = str(uuid.uuid4())
    model = request.model or settings.default_provider
    embedding = embed_text(request.prompt)

    # 1. Semantic cache lookup (scoped to the requested model) — return instantly on a hit.
    match = await cache_service.find_similar(session, embedding, model)
    if match is not None:
        return ChatResponse(
            response=match.response,
            cache_hit=True,
            similarity=match.similarity,
            provider="cache",
            request_id=request_id,
        )

    # 2. Cache miss — queue the request and wait for the worker's result.
    await queue_service.enqueue_request(
        {
            "request_id": request_id,
            "prompt": request.prompt,
            "model": model,
            "user_id": request.user_id,
            "session_id": request.session_id,
        }
    )

    result = await queue_service.wait_for_result(
        request_id, settings.worker_timeout_seconds
    )
    if result is None:
        raise HTTPException(
            status_code=504, detail="LLM worker timed out. Please try again."
        )
    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    return ChatResponse(
        response=result["response"],
        cache_hit=False,
        similarity=None,
        provider=result["provider"],
        request_id=request_id,
    )
