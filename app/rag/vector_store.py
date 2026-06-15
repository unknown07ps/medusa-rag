"""
Vector store abstraction layer.

Supports FAISS (default, local) and ChromaDB (persistent).
Both backends expose the same interface so the RAG pipeline doesn't care which is active.
"""
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

import structlog
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.monitoring.metrics import RETRIEVAL_LATENCY, RETRIEVAL_SCORE

logger = structlog.get_logger(__name__)


class VectorStoreBackend(ABC):
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> List[str]:
        ...

    @abstractmethod
    async def similarity_search_with_score(
        self, query: str, k: int
    ) -> List[Tuple[Document, float]]:
        ...

    @abstractmethod
    async def delete_documents(self, doc_ids: List[str]) -> None:
        ...


class FAISSBackend(VectorStoreBackend):
    def __init__(self, embeddings: OpenAIEmbeddings):
        self.embeddings = embeddings
        self.index_path = Path(settings.FAISS_INDEX_PATH)
        self._store = None

    async def _get_store(self):
        if self._store is not None:
            return self._store
        from langchain_community.vectorstores import FAISS

        if self.index_path.exists():
            self._store = FAISS.load_local(
                str(self.index_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("FAISS index loaded from disk", path=str(self.index_path))
        else:
            self._store = None
        return self._store

    async def add_documents(self, documents: List[Document]) -> List[str]:
        from langchain_community.vectorstores import FAISS

        store = await self._get_store()
        if store is None:
            self._store = await FAISS.afrom_documents(documents, self.embeddings)
        else:
            ids = await store.aadd_documents(documents)
            self._store = store

        self.index_path.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self.index_path))
        logger.info("FAISS index saved", chunk_count=len(documents))
        return [str(i) for i in range(len(documents))]

    async def similarity_search_with_score(
        self, query: str, k: int
    ) -> List[Tuple[Document, float]]:
        store = await self._get_store()
        if store is None:
            return []
        return await store.asimilarity_search_with_score(query, k=k)

    async def delete_documents(self, doc_ids: List[str]) -> None:
        store = await self._get_store()
        if store and hasattr(store, "delete"):
            store.delete(doc_ids)
            store.save_local(str(self.index_path))


class ChromaBackend(VectorStoreBackend):
    def __init__(self, embeddings: OpenAIEmbeddings):
        self.embeddings = embeddings
        self._store = None

    async def _get_store(self):
        if self._store is not None:
            return self._store
        from langchain_community.vectorstores import Chroma

        self._store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        return self._store

    async def add_documents(self, documents: List[Document]) -> List[str]:
        store = await self._get_store()
        ids = store.add_documents(documents)
        store.persist()
        return ids

    async def similarity_search_with_score(
        self, query: str, k: int
    ) -> List[Tuple[Document, float]]:
        store = await self._get_store()
        return store.similarity_search_with_score(query, k=k)

    async def delete_documents(self, doc_ids: List[str]) -> None:
        store = await self._get_store()
        store.delete(doc_ids)
        store.persist()


class VectorStoreManager:
    def __init__(self):
        self._backend: Optional[VectorStoreBackend] = None
        self._embeddings: Optional[OpenAIEmbeddings] = None

    async def initialize(self) -> None:
        self._embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
        )
        if settings.VECTOR_STORE_TYPE == "chroma":
            self._backend = ChromaBackend(self._embeddings)
            logger.info("Using ChromaDB backend")
        else:
            self._backend = FAISSBackend(self._embeddings)
            logger.info("Using FAISS backend")

    async def close(self) -> None:
        pass

    async def add_documents(self, documents: List[Document]) -> List[str]:
        return await self._backend.add_documents(documents)

    async def retrieve(
        self,
        query: str,
        k: int,
    ) -> List[Tuple[Document, float]]:
        start = time.perf_counter()
        results = await self._backend.similarity_search_with_score(query, k=k)
        elapsed = time.perf_counter() - start

        RETRIEVAL_LATENCY.labels(vector_store_type=settings.VECTOR_STORE_TYPE).observe(elapsed)

        for rank, (_, score) in enumerate(results):
            RETRIEVAL_SCORE.labels(result_rank=str(rank)).observe(float(score))

        return results

    async def delete_documents(self, doc_ids: List[str]) -> None:
        await self._backend.delete_documents(doc_ids)


vector_store_manager = VectorStoreManager()
