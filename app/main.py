import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.routes import query, documents, health, prompts
from app.monitoring.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    IN_PROGRESS_REQUESTS,
)
from app.core.config import settings
from app.core.logger import get_logger
from app.rag.vector_store import vector_store_manager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Medusa RAG API", version=settings.APP_VERSION)
    await vector_store_manager.initialize()
    logger.info("Vector store initialized")
    yield
    logger.info("Shutting down Medusa RAG API")
    await vector_store_manager.close()


app = FastAPI(
    title="Medusa RAG API",
    description="Production-grade RAG API with observability, prompt versioning, and fallback chains.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    route = request.url.path
    method = request.method

    IN_PROGRESS_REQUESTS.labels(endpoint=route).inc()
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
        REQUEST_COUNT.labels(
            method=method,
            endpoint=route,
            status_code=str(status_code),
        ).inc()
        return response
    except Exception as exc:
        REQUEST_COUNT.labels(
            method=method,
            endpoint=route,
            status_code="500",
        ).inc()
        logger.error(
            "Unhandled exception",
            request_id=request_id,
            path=route,
            error=str(exc),
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    finally:
        latency = time.perf_counter() - start_time
        REQUEST_LATENCY.labels(endpoint=route).observe(latency)
        IN_PROGRESS_REQUESTS.labels(endpoint=route).dec()


# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(query.router, prefix="/api/v1/query", tags=["query"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
