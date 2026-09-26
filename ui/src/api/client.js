// API routing is environment-aware.
// Production/Docker: same-origin requests are proxied by ui/nginx.conf to the api container.
// Local React dev: defaults to http://localhost:8000.
const BASE =
  process.env.REACT_APP_API_URL ||
  (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  const type = res.headers.get("content-type") || "";
  const data = type.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const detail = data && typeof data === "object" ? data.detail : null;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return data;
}

export async function queryMedusa({ query, prompt_version, use_cache }) {
  return request("/api/v1/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, prompt_version, use_cache }),
  });
}

export async function ingestText({ text, source_name }) {
  return request("/api/v1/documents/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, source_name }),
  });
}

export async function ingestFile(file) {
  const form = new FormData();
  form.append("file", file);
  return request("/api/v1/documents/upload", { method: "POST", body: form });
}

export async function listPrompts() {
  return request("/api/v1/prompts");
}

export async function fetchHealth() {
  return request("/health");
}

export async function fetchRawMetrics() {
  const raw = await request("/metrics");
  return typeof raw === "string" ? raw : "";
}

export function extractMetrics(raw) {
  const totalLines = [...raw.matchAll(/^medusa_http_requests_total\{[^}]+\}\s+([\d.e+]+)/gm)];
  const total = totalLines.reduce((s, m) => s + parseFloat(m[1]), 0);

  const errorLines = [...raw.matchAll(/^medusa_http_requests_total\{[^}]*status_code="5\d\d"[^}]*\}\s+([\d.e+]+)/gm)];
  const errors = errorLines.reduce((s, m) => s + parseFloat(m[1]), 0);

  const metric = (pattern) => {
    const m = raw.match(pattern);
    return m ? parseFloat(m[1]) : 0;
  };

  const cacheHit = metric(/medusa_cache_hits_total\{result="hit"\}\s+([\d.e+]+)/m);
  const cacheMiss = metric(/medusa_cache_hits_total\{result="miss"\}\s+([\d.e+]+)/m);
  const fb1 = metric(/medusa_fallback_triggered_total\{fallback_level="level1"\}\s+([\d.e+]+)/m);
  const fb2 = metric(/medusa_fallback_triggered_total\{fallback_level="level2"\}\s+([\d.e+]+)/m);
  const docsIngested = metric(/medusa_documents_ingested_total\{status="success"\}\s+([\d.e+]+)/m);

  const promptLines = [...raw.matchAll(/medusa_llm_tokens_total\{[^}]*token_type="(\w+)"[^}]*\}\s+([\d.e+]+)/gm)];
  let promptTokens = 0;
  let completionTokens = 0;
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
