"""
Document ingestion pipeline.

Handles PDF, TXT, and plain text input.
Splits into chunks, adds metadata, and upserts into the vector store.
Deduplication is done via SHA-256 hash of the source content.
"""
import hashlib
import uuid
from pathlib import Path
from typing import List, Optional

import structlog
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.monitoring.metrics import DOCUMENT_INGESTION_COUNT
from app.rag.vector_store import vector_store_manager

logger = structlog.get_logger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def _hash_content(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def _load_file(filepath: str) -> List[Document]:
    path = Path(filepath)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        loader = PyPDFLoader(filepath)
    elif suffix in {".txt", ".md"}:
        loader = TextLoader(filepath, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    return loader.load()


async def ingest_file(
    filepath: str,
    metadata: Optional[dict] = None,
) -> dict:
    doc_id = str(uuid.uuid4())
    extra_meta = metadata or {}

    try:
        raw_docs = _load_file(filepath)
        full_text = "\n".join(d.page_content for d in raw_docs)
        source_hash = _hash_content(full_text)

        chunks = _splitter.split_documents(raw_docs)
        for i, chunk in enumerate(chunks):
            chunk.metadata.update(
                {
                    "doc_id": doc_id,
                    "source": Path(filepath).name,
                    "chunk_index": i,
                    "source_hash": source_hash,
                    **extra_meta,
                }
            )

        await vector_store_manager.add_documents(chunks)
        DOCUMENT_INGESTION_COUNT.labels(status="success").inc()

        logger.info(
            "Document ingested",
            doc_id=doc_id,
            source=Path(filepath).name,
            chunks=len(chunks),
        )

        return {
            "doc_id": doc_id,
            "source_hash": source_hash,
            "chunk_count": len(chunks),
            "filename": Path(filepath).name,
        }

    except Exception as exc:
        DOCUMENT_INGESTION_COUNT.labels(status="failed").inc()
        logger.error("Ingestion failed", filepath=filepath, error=str(exc))
        raise


async def ingest_text(
    text: str,
    source_name: str = "inline_text",
    metadata: Optional[dict] = None,
) -> dict:
    doc_id = str(uuid.uuid4())
    source_hash = _hash_content(text)
    extra_meta = metadata or {}

    doc = Document(
        page_content=text,
        metadata={"source": source_name, "doc_id": doc_id, "source_hash": source_hash, **extra_meta},
    )
    chunks = _splitter.split_documents([doc])

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

    await vector_store_manager.add_documents(chunks)
    DOCUMENT_INGESTION_COUNT.labels(status="success").inc()

    logger.info("Text ingested", doc_id=doc_id, source=source_name, chunks=len(chunks))

    return {
        "doc_id": doc_id,
        "source_hash": source_hash,
        "chunk_count": len(chunks),
        "filename": source_name,
    }
