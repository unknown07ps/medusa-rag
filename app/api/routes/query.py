from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.rag.cache import get_cached_response, set_cached_response
from app.rag.pipeline import run_rag_pipeline

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="User question")
    prompt_version: Optional[str] = Field(None, description="Prompt version to use (e.g. 'v1', 'v2')")
    use_cache: bool = Field(True, description="Whether to use Redis cache")


class QueryResponse(BaseModel):
    answer: str
    prompt_version: str
    fallback_level: Optional[str]
    retrieved_chunks: int
    retrieval_scores: List[float]
    trace_id: str
    cached: bool = False


@router.post("", response_model=QueryResponse)
async def query_documents(
    body: QueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", "unknown")
    effective_version = body.prompt_version or "v1"

    if body.use_cache:
        cached = await get_cached_response(body.query, effective_version)
        if cached:
            return QueryResponse(**cached, cached=True)

    try:
        result = await run_rag_pipeline(
            query=body.query,
            prompt_version=body.prompt_version,
            request_id=request_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(exc)}")

    tracer = result.pop("tracer", None)
    if tracer:
        await tracer.persist(db)

    response = QueryResponse(**result, cached=False)

    if body.use_cache:
        await set_cached_response(body.query, effective_version, result)

    return response
