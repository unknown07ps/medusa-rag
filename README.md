# Medusa RAG

A production-grade Retrieval-Augmented Generation (RAG) API built with FastAPI, LangChain, and a full observability stack. Designed to be monitored, debugged, and improved in production — not just demoed.

---

## Architecture

```
Client
  │
  ▼
FastAPI (Observability Middleware)
  │
  ├── Redis Cache (query deduplication)
  │
  ▼
RAG Pipeline
  ├── Stage 1: Primary Retrieval (FAISS / ChromaDB)
  │     └── Score ≥ threshold → LLM answer
  │
  ├── Stage 2: Fallback Level 1 (broaden search, lower threshold)
  │     └── Still poor → Stage 3
  │
  └── Stage 3: Fallback Level 2 (LLM general knowledge + disclaimer)
        └── Answer returned with fallback_level: "level2"

Tracing → PostgreSQL (query_traces table)
Metrics → Prometheus → Grafana
Optional → LangSmith
```

---

## Features

- **Fallback Chain** — Two-level degradation strategy when retrieval quality is low, so the API always returns a useful answer instead of failing silently
- **Prompt Versioning** — YAML-based prompt registry; swap or A/B test prompts without redeploying the service
- **Full Observability** — Prometheus metrics for request rate, p95 latency, LLM token usage, retrieval scores, cache hit rate, and fallback frequency; pre-built Grafana dashboard included
- **Structured Tracing** — Every request produces a span tree persisted to Postgres; optional LangSmith forwarding
- **Redis Cache** — Identical queries (same prompt version) are cached for 5 minutes
- **Dual Vector Store** — Switchable between FAISS (local, fast) and ChromaDB (persistent) via environment variable
- **Document Ingestion API** — Upload PDFs, TXT, or MD files; or POST raw text directly

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn |
| RAG | LangChain, OpenAI (gpt-4o-mini) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | FAISS (default) / ChromaDB |
| Cache | Redis |
| Database | PostgreSQL (trace persistence) |
| Metrics | Prometheus + Grafana |
| Tracing | Custom span tracer + LangSmith (optional) |
| Logging | structlog (JSON) |
| Containers | Docker + Docker Compose |

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### 1. Clone and configure

```bash
git clone https://github.com/unknown07ps/medusa-rag.git
cd medusa-rag
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 2. Start all services

```bash
docker compose up --build
```

This starts: API (port 8000), Postgres (5432), Redis (6379), Prometheus (9090), Grafana (3000).

### 3. Ingest a document

```bash
# Upload a PDF
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@your_document.pdf"

# Or POST raw text
curl -X POST http://localhost:8000/api/v1/documents/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Your content here", "source_name": "manual_entry"}'
```

### 4. Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the document say about X?", "prompt_version": "v1"}'
```

**Response:**
```json
{
  "answer": "According to test.pdf, ...",
  "prompt_version": "v1",
  "fallback_level": null,
  "retrieved_chunks": 4,
  "retrieval_scores": [0.87, 0.81, 0.74, 0.69],
  "trace_id": "3f2a1b...",
  "cached": false
}
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/health/ready` | Readiness probe |
| POST | `/api/v1/query` | RAG query |
| POST | `/api/v1/documents/upload` | Upload PDF / TXT / MD |
| POST | `/api/v1/documents/text` | Ingest raw text |
| GET | `/api/v1/prompts` | List prompt versions |
| GET | `/api/v1/prompts/{version}` | Inspect a prompt version |
| GET | `/metrics` | Prometheus metrics scrape endpoint |

Full interactive docs: `http://localhost:8000/docs`

---

## UI

A React dashboard is included and starts automatically with Docker Compose.

Open `http://localhost:3001` after `docker compose up --build`.

**Query tab** — select prompt version, toggle cache, send a question, see the answer with retrieval score bars, fallback level, trace ID, and a clickable query history.

**Ingest tab** — upload a PDF/TXT/MD file or paste raw text directly.

**Metrics sidebar** — live pull from `/metrics` every 10 seconds: request count, error rate, cache hit/miss rate bar, fallback level breakdown, LLM token totals, documents ingested.

---

## Prompt Versioning

Prompts live in `app/prompts/versions/` as YAML files. No restart needed — the registry reads from disk on every request.

```yaml
# app/prompts/versions/v3.yaml
version: "v3"
description: "My new experimental prompt"
max_context_chunks: 4
temperature_override: 0.0

system_template: |
  You are Medusa ...

user_template: |
  Context: {context}
  Question: {query}
  Answer:
```

Switch the default via `DEFAULT_PROMPT_VERSION=v3` in `.env`, or pass `"prompt_version": "v3"` per request.

---

## Observability

### Grafana Dashboard

Open `http://localhost:3000` → login `admin / medusa` → dashboard auto-loads.

Panels:
- Request rate and error rate
- P95 HTTP and RAG pipeline latency
- Fallback trigger rate (level 1 vs level 2)
- LLM token usage (prompt vs completion)
- Retrieval score distribution
- Cache hit rate
- Active prompt version

### Key Prometheus Metrics

```
medusa_http_requests_total
medusa_http_request_duration_seconds
medusa_rag_query_duration_seconds
medusa_fallback_triggered_total
medusa_llm_tokens_total
medusa_retrieval_score
medusa_cache_hits_total
```

### LangSmith (optional)

Set in `.env`:
```
ENABLE_LANGSMITH=true
LANGSMITH_API_KEY=ls__your_key
LANGCHAIN_TRACING_V2=true
```

---

## Fallback Chain

| Level | Trigger | Behavior |
|---|---|---|
| Normal | Top-K scores ≥ `RETRIEVAL_SCORE_THRESHOLD` (0.30) | Answer from retrieved context |
| Level 1 | Scores below threshold | Broaden search (2× K, lower threshold 0.15) |
| Level 2 | Still no good results | LLM answers from general knowledge with explicit disclaimer |

Tune thresholds in `.env`:
```
RETRIEVAL_SCORE_THRESHOLD=0.30
FALLBACK_SCORE_THRESHOLD=0.15
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests are fully offline — OpenAI and vector store are mocked.

---

## Project Structure

```
medusa-rag/
├── app/
│   ├── main.py                  # FastAPI app, middleware
│   ├── api/routes/              # query, documents, health, prompts
│   ├── core/                    # config, database, logger
│   ├── rag/                     # pipeline, vector_store, ingestion, cache
│   ├── monitoring/              # metrics, tracer, ORM models
│   └── prompts/                 # registry + versioned YAML prompts
├── tests/
├── docker/                      # Dockerfile, prometheus.yml
├── grafana/                     # dashboard JSON + provisioning
├── scripts/                     # init_db.sql
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Author

**Sagar Prajapati** — [GitHub](https://github.com/unknown07ps)
