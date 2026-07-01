from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
