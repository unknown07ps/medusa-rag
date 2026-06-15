from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LLM
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 1024

    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Vector store
    VECTOR_STORE_TYPE: str = "faiss"         # faiss | chroma
    FAISS_INDEX_PATH: str = "./data/faiss_index"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_NAME: str = "medusa_docs"

    # Retrieval
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_SCORE_THRESHOLD: float = 0.3    # below this -> fallback triggered
    FALLBACK_TOP_K: int = 3                   # k used in fallback (broader search)
    FALLBACK_SCORE_THRESHOLD: float = 0.15    # absolute floor; below this -> no-context answer

    # Prompt versioning
    PROMPT_STORE_PATH: str = "./app/prompts/versions"
    DEFAULT_PROMPT_VERSION: str = "v1"

    # Tracing
    ENABLE_LANGSMITH: bool = False
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "medusa-rag"
    LANGCHAIN_TRACING_V2: bool = False

    # Postgres (for request audit log)
    DATABASE_URL: str = "postgresql+asyncpg://medusa:medusa@postgres:5432/medusa"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
