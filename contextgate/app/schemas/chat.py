from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: str = "mock"
    user_id: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    cache_hit: bool
    similarity: float | None
    provider: str
    request_id: str
