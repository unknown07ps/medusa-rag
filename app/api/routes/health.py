from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    vector_store: str


@router.get("", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        vector_store=settings.VECTOR_STORE_TYPE,
    )


@router.get("/ready")
async def readiness_probe():
    # Can be extended to check DB / Redis connectivity
    return {"ready": True}
