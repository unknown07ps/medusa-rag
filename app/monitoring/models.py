from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QueryTrace(Base):
    __tablename__ = "query_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    fallback_level: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retrieval_scores: Mapped[List[float]] = mapped_column(JSONB, default=list)
    token_usage: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    spans: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
