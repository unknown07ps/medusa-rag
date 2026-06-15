"""
Custom request tracer.

Records a structured span tree for every RAG query, persists it to Postgres,
and optionally forwards to LangSmith when ENABLE_LANGSMITH=true.
"""
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.monitoring.models import QueryTrace

logger = structlog.get_logger(__name__)


@dataclass
class Span:
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def finish(self, **meta) -> "Span":
        self.end_time = time.perf_counter()
        self.metadata.update(meta)
        return self

    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.perf_counter() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


class RAGTracer:
    """
    Lightweight tracer that collects spans for a single RAG request.
    Compatible with LangSmith's run schema when forwarding is enabled.
    """

    def __init__(self, request_id: str, query: str, prompt_version: str):
        self.trace_id = str(uuid.uuid4())
        self.request_id = request_id
        self.query = query
        self.prompt_version = prompt_version
        self.spans: List[Span] = []
        self.fallback_level: Optional[str] = None
        self.answer: Optional[str] = None
        self.retrieval_scores: List[float] = []
        self.token_usage: Dict[str, int] = {}
        self.started_at = datetime.now(timezone.utc)

    def start_span(self, name: str) -> Span:
        span = Span(name=name)
        self.spans.append(span)
        return span

    def set_fallback(self, level: str) -> None:
        self.fallback_level = level
        logger.warning(
            "Fallback triggered",
            trace_id=self.trace_id,
            level=level,
            query=self.query[:100],
        )

    def set_answer(self, answer: str) -> None:
        self.answer = answer

    def set_retrieval_scores(self, scores: List[float]) -> None:
        self.retrieval_scores = scores

    def set_token_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.token_usage = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "query": self.query,
            "prompt_version": self.prompt_version,
            "fallback_level": self.fallback_level,
            "answer_length": len(self.answer) if self.answer else 0,
            "retrieval_scores": self.retrieval_scores,
            "token_usage": self.token_usage,
            "spans": [
                {
                    "name": s.name,
                    "duration_ms": round(s.duration_ms, 2),
                    "metadata": s.metadata,
                    "error": s.error,
                }
                for s in self.spans
            ],
        }

    async def persist(self, db: AsyncSession) -> None:
        record = QueryTrace(
            trace_id=self.trace_id,
            request_id=self.request_id,
            query=self.query,
            prompt_version=self.prompt_version,
            fallback_level=self.fallback_level,
            answer=self.answer,
            retrieval_scores=self.retrieval_scores,
            token_usage=self.token_usage,
            spans=[
                {
                    "name": s.name,
                    "duration_ms": round(s.duration_ms, 2),
                    "metadata": s.metadata,
                    "error": s.error,
                }
                for s in self.spans
            ],
            created_at=self.started_at,
        )
        db.add(record)
        await db.flush()
        logger.info(
            "Trace persisted",
            trace_id=self.trace_id,
            fallback=self.fallback_level,
        )

        if settings.ENABLE_LANGSMITH:
            await self._forward_to_langsmith()

    async def _forward_to_langsmith(self) -> None:
        try:
            from langsmith import Client
            from langsmith.schemas import RunCreate

            client = Client(api_key=settings.LANGSMITH_API_KEY)
            client.create_run(
                RunCreate(
                    id=self.trace_id,
                    name="medusa_rag_query",
                    run_type="chain",
                    inputs={"query": self.query, "prompt_version": self.prompt_version},
                    outputs={"answer": self.answer},
                    extra={"metadata": self.to_dict()},
                    project_name=settings.LANGSMITH_PROJECT,
                )
            )
        except Exception as exc:
            logger.warning("LangSmith forward failed", error=str(exc))
