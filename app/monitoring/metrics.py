from prometheus_client import Counter, Histogram, Gauge, Summary

# HTTP layer
REQUEST_COUNT = Counter(
    "medusa_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "medusa_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

IN_PROGRESS_REQUESTS = Gauge(
    "medusa_http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["endpoint"],
)

# RAG pipeline
RAG_QUERY_LATENCY = Histogram(
    "medusa_rag_query_duration_seconds",
    "End-to-end RAG query latency",
    ["prompt_version", "fallback_triggered"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

RETRIEVAL_LATENCY = Histogram(
    "medusa_retrieval_duration_seconds",
    "Vector store retrieval latency",
    ["vector_store_type"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0],
)

LLM_LATENCY = Histogram(
    "medusa_llm_duration_seconds",
    "LLM call latency",
    ["model", "prompt_version"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

LLM_TOKEN_COUNT = Counter(
    "medusa_llm_tokens_total",
    "Total LLM tokens used",
    ["model", "token_type"],  # token_type: prompt | completion
)

RETRIEVAL_SCORE = Histogram(
    "medusa_retrieval_score",
    "Similarity scores of retrieved documents",
    ["result_rank"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

FALLBACK_COUNTER = Counter(
    "medusa_fallback_triggered_total",
    "Times the fallback retrieval chain was triggered",
    ["fallback_level"],  # level1 (broader search) | level2 (no-context answer)
)

DOCUMENT_INGESTION_COUNT = Counter(
    "medusa_documents_ingested_total",
    "Total documents ingested into vector store",
    ["status"],  # success | failed
)

CACHE_HIT_COUNT = Counter(
    "medusa_cache_hits_total",
    "Redis cache hit/miss counts",
    ["result"],  # hit | miss
)

ACTIVE_PROMPT_VERSION = Gauge(
    "medusa_active_prompt_version_info",
    "Currently active prompt version (label-based info metric)",
    ["version"],
)

RAG_ANSWER_QUALITY = Summary(
    "medusa_rag_answer_quality_score",
    "Self-reported answer quality scores (0-1)",
    ["prompt_version"],
)
