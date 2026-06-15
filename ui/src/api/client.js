const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export async function queryMedusa({ query, prompt_version, use_cache }) {
  const res = await fetch(`${BASE}/api/v1/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, prompt_version, use_cache }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Query failed");
  return res.json();
}

export async function ingestText({ text, source_name }) {
  const res = await fetch(`${BASE}/api/v1/documents/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_name }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Ingest failed");
  return res.json();
}

export async function ingestFile(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/v1/documents/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
  return res.json();
}

export async function listPrompts() {
  const res = await fetch(`${BASE}/api/v1/prompts`);
  if (!res.ok) throw new Error("Failed to fetch prompts");
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("API unreachable");
  return res.json();
}

export async function fetchRawMetrics() {
  const res = await fetch(`${BASE}/metrics`);
  if (!res.ok) return "";
  return res.text();
}

function parseMetric(raw, name) {
  const match = raw.match(new RegExp(`^${name}\\{[^}]*\\}\\s+([\\d.e+]+)`, "m")) ||
                raw.match(new RegExp(`^${name}\\s+([\\d.e+]+)`, "m"));
  return match ? parseFloat(match[1]) : null;
}

export function extractMetrics(raw) {
  const totalLines = [...raw.matchAll(/^medusa_http_requests_total\{[^}]+\}\s+([\d.e+]+)/gm)];
  const total = totalLines.reduce((s, m) => s + parseFloat(m[1]), 0);

  const errorLines = [...raw.matchAll(/^medusa_http_requests_total\{[^}]*status_code="5\d\d"[^}]*\}\s+([\d.e+]+)/gm)];
  const errors = errorLines.reduce((s, m) => s + parseFloat(m[1]), 0);

  const cacheHit = (() => {
    const m = raw.match(/medusa_cache_hits_total\{result="hit"\}\s+([\d.e+]+)/m);
    return m ? parseFloat(m[1]) : 0;
  })();
  const cacheMiss = (() => {
    const m = raw.match(/medusa_cache_hits_total\{result="miss"\}\s+([\d.e+]+)/m);
    return m ? parseFloat(m[1]) : 0;
  })();

  const fb1 = (() => {
    const m = raw.match(/medusa_fallback_triggered_total\{fallback_level="level1"\}\s+([\d.e+]+)/m);
    return m ? parseFloat(m[1]) : 0;
  })();
  const fb2 = (() => {
    const m = raw.match(/medusa_fallback_triggered_total\{fallback_level="level2"\}\s+([\d.e+]+)/m);
    return m ? parseFloat(m[1]) : 0;
  })();

  const docsIngested = (() => {
    const m = raw.match(/medusa_documents_ingested_total\{status="success"\}\s+([\d.e+]+)/m);
    return m ? parseFloat(m[1]) : 0;
  })();

  const promptLines = [...raw.matchAll(/medusa_llm_tokens_total\{[^}]*token_type="(\w+)"[^}]*\}\s+([\d.e+]+)/gm)];
  let promptTokens = 0, completionTokens = 0;
  for (const m of promptLines) {
    if (m[1] === "prompt") promptTokens += parseFloat(m[2]);
    if (m[1] === "completion") completionTokens += parseFloat(m[2]);
  }

  return {
    total_requests: Math.round(total),
    error_requests: Math.round(errors),
    cache_hit: Math.round(cacheHit),
    cache_miss: Math.round(cacheMiss),
    fallback_level1: Math.round(fb1),
    fallback_level2: Math.round(fb2),
    docs_ingested: Math.round(docsIngested),
    prompt_tokens: Math.round(promptTokens),
    completion_tokens: Math.round(completionTokens),
  };
}
