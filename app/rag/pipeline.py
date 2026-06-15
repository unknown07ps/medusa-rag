"""
RAG pipeline with a two-level fallback chain.

Level 0 (normal):   retrieve top-K with score >= RETRIEVAL_SCORE_THRESHOLD
Level 1 (fallback): score below threshold -> broaden search (larger K, lower threshold)
Level 2 (fallback): still poor quality -> answer from LLM general knowledge + disclaimer

Each level is traced as a span and recorded in Prometheus.
"""
import time
from typing import List, Optional, Tuple

import structlog
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI

from app.core.config import settings
from app.monitoring.metrics import (
    FALLBACK_COUNTER,
    LLM_LATENCY,
    LLM_TOKEN_COUNT,
    RAG_QUERY_LATENCY,
)
from app.monitoring.tracer import RAGTracer
from app.prompts.registry import PromptTemplate, prompt_registry
from app.rag.vector_store import vector_store_manager

logger = structlog.get_logger(__name__)

_openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _format_context(results: List[Tuple[Document, float]]) -> str:
    parts = []
    for i, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        parts.append(f"[Chunk {i} | source: {source} | score: {score:.3f}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


async def _call_llm(
    system_prompt: str,
    user_prompt: str,
    template: PromptTemplate,
    tracer: RAGTracer,
) -> str:
    temperature = (
        template.temperature_override
        if template.temperature_override is not None
        else settings.LLM_TEMPERATURE
    )

    span = tracer.start_span("llm_call")
    start = time.perf_counter()

    response = await _openai_client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=settings.LLM_MAX_TOKENS,
    )

    elapsed = time.perf_counter() - start
    usage = response.usage

    LLM_LATENCY.labels(
        model=settings.LLM_MODEL,
        prompt_version=template.version,
    ).observe(elapsed)

    if usage:
        LLM_TOKEN_COUNT.labels(model=settings.LLM_MODEL, token_type="prompt").inc(
            usage.prompt_tokens
        )
        LLM_TOKEN_COUNT.labels(model=settings.LLM_MODEL, token_type="completion").inc(
            usage.completion_tokens
        )
        tracer.set_token_usage(usage.prompt_tokens, usage.completion_tokens)

    answer = response.choices[0].message.content.strip()
    span.finish(
        model=settings.LLM_MODEL,
        temperature=temperature,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
    )
    return answer


async def run_rag_pipeline(
    query: str,
    prompt_version: Optional[str],
    request_id: str,
) -> dict:
    """
    Execute the RAG pipeline and return a structured response.
    """
    pipeline_start = time.perf_counter()
    template = prompt_registry.get_prompt(prompt_version)
    tracer = RAGTracer(
        request_id=request_id,
        query=query,
        prompt_version=template.version,
    )

    fallback_triggered = "false"
    fallback_level = None

    # --- Stage 1: primary retrieval ---
    retrieval_span = tracer.start_span("retrieval_primary")
    results = await vector_store_manager.retrieve(query, k=settings.RETRIEVAL_TOP_K)
    retrieval_span.finish(k=settings.RETRIEVAL_TOP_K, results_count=len(results))

    scores = [float(score) for _, score in results]
    tracer.set_retrieval_scores(scores)

    good_results = [(doc, score) for doc, score in results if score >= settings.RETRIEVAL_SCORE_THRESHOLD]

    # --- Stage 2: fallback level 1 (broaden search) ---
    if not good_results:
        fallback_triggered = "true"
        fallback_level = "level1"
        tracer.set_fallback("level1")
        FALLBACK_COUNTER.labels(fallback_level="level1").inc()

        fb_span = tracer.start_span("retrieval_fallback_level1")
        results = await vector_store_manager.retrieve(query, k=settings.FALLBACK_TOP_K * 2)
        fb_span.finish(k=settings.FALLBACK_TOP_K * 2, results_count=len(results))

        good_results = [
            (doc, score) for doc, score in results
            if score >= settings.FALLBACK_SCORE_THRESHOLD
        ]

    # --- Stage 3: fallback level 2 (no-context LLM answer) ---
    if not good_results:
        fallback_level = "level2"
        tracer.set_fallback("level2")
        FALLBACK_COUNTER.labels(fallback_level="level2").inc()

        no_context_system = (
            "You are Medusa, a research assistant. "
            "No relevant documents were found for this query. "
            "Answer from your general knowledge and explicitly state that no documents were retrieved."
        )
        no_context_user = f"Question: {query}"

        answer = await _call_llm(no_context_system, no_context_user, template, tracer)
        tracer.set_answer(answer)

        total_elapsed = time.perf_counter() - pipeline_start
        RAG_QUERY_LATENCY.labels(
            prompt_version=template.version,
            fallback_triggered=fallback_triggered,
        ).observe(total_elapsed)

        return {
            "answer": answer,
            "prompt_version": template.version,
            "fallback_level": fallback_level,
            "retrieved_chunks": 0,
            "retrieval_scores": scores,
            "trace_id": tracer.trace_id,
        }

    # --- Stage 4: format context and call LLM ---
    context = _format_context(good_results[: template.max_context_chunks])
    system_prompt, user_prompt = prompt_registry.format_prompt(template, context, query)

    answer = await _call_llm(system_prompt, user_prompt, template, tracer)
    tracer.set_answer(answer)

    total_elapsed = time.perf_counter() - pipeline_start
    RAG_QUERY_LATENCY.labels(
        prompt_version=template.version,
        fallback_triggered=fallback_triggered,
    ).observe(total_elapsed)

    logger.info(
        "RAG pipeline completed",
        trace_id=tracer.trace_id,
        prompt_version=template.version,
        chunks_used=len(good_results),
        fallback=fallback_level,
        latency_ms=round(total_elapsed * 1000, 2),
    )

    return {
        "answer": answer,
        "prompt_version": template.version,
        "fallback_level": fallback_level,
        "retrieved_chunks": len(good_results),
        "retrieval_scores": scores,
        "trace_id": tracer.trace_id,
        "tracer": tracer,
    }
