from fastapi import APIRouter
from sqlalchemy import text

from app.core.cache import get_redis
from app.core.database import AsyncSessionLocal
from app.ml.pipeline import pipeline_manager
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    db_status = "ok"
    redis_status = "ok"

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        r = await get_redis()
        await r.ping()
    except Exception:
        redis_status = "error"

    return HealthResponse(
        status="ok" if db_status == "ok" and redis_status == "ok" else "degraded",
        database=db_status,
        redis=redis_status,
        model_loaded=pipeline_manager.is_loaded(),
    )
