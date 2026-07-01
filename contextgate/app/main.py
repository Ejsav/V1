import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.database import init_db
from app.routes import chat, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contextgate")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as exc:  # keep the API importable even if the DB isn't ready
        logger.warning("Database initialization skipped: %s", exc)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(chat.router)
