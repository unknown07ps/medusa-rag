"""
Integration tests for Medusa RAG API.
Uses httpx AsyncClient against the FastAPI app directly (no Docker needed).
Mocks OpenAI and vector store so tests run offline.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.documents import Document

from app.main import app


@pytest.fixture
def mock_vector_store():
    with patch("app.rag.pipeline.vector_store_manager") as mock:
        mock.retrieve = AsyncMock(
            return_value=[
                (Document(page_content="Medusa is a production RAG system.", metadata={"source": "test.pdf"}), 0.85),
                (Document(page_content="It uses FAISS for vector retrieval.", metadata={"source": "test.pdf"}), 0.78),
            ]
        )
        yield mock


@pytest.fixture
def mock_openai():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Medusa is a production RAG system with observability."
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50

    with patch("app.rag.pipeline._openai_client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        yield mock_client


@pytest.fixture
def mock_db():
    with patch("app.api.routes.query.get_db") as mock:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        mock.return_value.__aiter__ = AsyncMock(return_value=iter([session]))

        async def _dep():
            yield session

        mock.return_value = _dep()
        yield session


@pytest.fixture
def mock_cache():
    with patch("app.api.routes.query.get_cached_response", return_value=None), \
         patch("app.api.routes.query.set_cached_response", return_value=None):
        yield


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_probe():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


@pytest.mark.asyncio
async def test_list_prompt_versions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/prompts")
    assert response.status_code == 200
    data = response.json()
    assert "versions" in data
    assert "v1" in data["versions"]
    assert "v2" in data["versions"]


@pytest.mark.asyncio
async def test_get_prompt_version():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/prompts/v1")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "v1"


@pytest.mark.asyncio
async def test_get_prompt_version_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/prompts/v99")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_query_endpoint(mock_vector_store, mock_openai, mock_cache):
    with patch("app.api.routes.query.get_db") as mock_get_db:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        async def _dep():
            yield session

        mock_get_db.return_value = _dep()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={"query": "What is Medusa?", "prompt_version": "v1", "use_cache": False},
            )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "trace_id" in data
    assert "prompt_version" in data
    assert data["prompt_version"] == "v1"
    assert data["retrieved_chunks"] > 0


@pytest.mark.asyncio
async def test_query_too_short():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/query",
            json={"query": "Hi", "use_cache": False},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_fallback_level2_triggered(mock_openai, mock_cache):
    with patch("app.rag.pipeline.vector_store_manager") as mock_vs, \
         patch("app.api.routes.query.get_db") as mock_get_db:

        mock_vs.retrieve = AsyncMock(return_value=[])

        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        async def _dep():
            yield session

        mock_get_db.return_value = _dep()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={"query": "Something completely unrelated to any document", "use_cache": False},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["fallback_level"] == "level2"
    assert data["retrieved_chunks"] == 0


@pytest.mark.asyncio
async def test_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert b"medusa_http_requests_total" in response.content
