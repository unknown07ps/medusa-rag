import { useState } from "react";
import { queryMedusa } from "../api/client";

export default function QueryPanel({ promptVersions, onQueryComplete }) {
  const [query, setQuery] = useState("");
  const [version, setVersion] = useState(promptVersions.default || "v1");
  const [useCache, setUseCache] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  async function handleSubmit() {
    if (!query.trim() || query.trim().length < 3) {
      setError("Query must be at least 3 characters.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await queryMedusa({
        query: query.trim(),
        prompt_version: version,
        use_cache: useCache,
      });
      setResult(data);
      setHistory((h) => [{ query: query.trim(), ...data, ts: new Date() }, ...h].slice(0, 10));
      onQueryComplete();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSubmit();
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Query Documents</h2>
        <p className="panel-desc">Ask anything about your ingested documents. Ctrl+Enter to send.</p>
      </div>

      <div className="query-controls">
        <div className="control-row">
          <label className="control-label">Prompt Version</label>
          <div className="version-pills">
            {(promptVersions.versions || ["v1", "v2"]).map((v) => (
              <button
                key={v}
                className={`pill ${version === v ? "pill-active" : ""}`}
                onClick={() => setVersion(v)}
              >
                {v}
              </button>
            ))}
          </div>
          <label className="cache-toggle">
            <input
              type="checkbox"
              checked={useCache}
              onChange={(e) => setUseCache(e.target.checked)}
            />
            <span>Use cache</span>
          </label>
        </div>

        <textarea
          className="query-input"
          placeholder="What does the document say about..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={4}
          disabled={loading}
        />

        <button
          className={`submit-btn ${loading ? "loading" : ""}`}
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? (
            <span className="spinner-row"><span className="spinner" /> Querying...</span>
          ) : "Send Query"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {result && <QueryResult result={result} />}

      {history.length > 1 && (
        <div className="history">
          <div className="history-title">Recent Queries</div>
          {history.slice(1).map((h, i) => (
            <div key={i} className="history-item" onClick={() => { setQuery(h.query); setResult(h); }}>
              <span className="history-q">{h.query.slice(0, 80)}{h.query.length > 80 ? "…" : ""}</span>
              <span className={`fallback-badge ${h.fallback_level ? "fallback-on" : "fallback-off"}`}>
                {h.fallback_level || "ok"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function QueryResult({ result }) {
  const [showChunks, setShowChunks] = useState(false);

  return (
    <div className="result-box">
      <div className="result-meta">
        <MetaBadge label="Prompt" value={result.prompt_version} />
        <MetaBadge
          label="Fallback"
          value={result.fallback_level || "none"}
          highlight={!!result.fallback_level}
        />
        <MetaBadge label="Chunks" value={result.retrieved_chunks} />
        <MetaBadge label="Cached" value={result.cached ? "yes" : "no"} />
        <MetaBadge label="Trace ID" value={result.trace_id?.slice(0, 8) + "…"} mono />
      </div>

      <div className="answer-label">Answer</div>
      <div className="answer-text">{result.answer}</div>

      {result.retrieval_scores?.length > 0 && (
        <div className="scores-section">
          <div className="scores-label">Retrieval Scores</div>
          <div className="scores-row">
            {result.retrieval_scores.map((s, i) => (
              <ScoreBar key={i} score={s} rank={i + 1} />
            ))}
          </div>
          <button
            className="toggle-chunks"
            onClick={() => setShowChunks((v) => !v)}
          >
            {showChunks ? "Hide" : "Show"} raw scores
          </button>
          {showChunks && (
            <pre className="raw-scores">
              {result.retrieval_scores.map((s, i) => `Chunk ${i + 1}: ${s.toFixed(4)}`).join("\n")}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

function MetaBadge({ label, value, highlight, mono }) {
  return (
    <div className={`meta-badge ${highlight ? "meta-highlight" : ""}`}>
      <span className="meta-label">{label}</span>
      <span className={`meta-value ${mono ? "mono" : ""}`}>{value}</span>
    </div>
  );
}

function ScoreBar({ score, rank }) {
  const pct = Math.min(100, Math.round(score * 100));
  const color = score >= 0.7 ? "#4ade80" : score >= 0.4 ? "#facc15" : "#f87171";
  return (
    <div className="score-bar-wrap" title={`Chunk ${rank}: ${score.toFixed(4)}`}>
      <div className="score-bar-label">#{rank}</div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="score-bar-val">{score.toFixed(2)}</div>
    </div>
  );
}
