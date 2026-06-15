export default function MetricsSidebar({ metrics, onRefresh }) {
  const cacheTotal = (metrics?.cache_hit || 0) + (metrics?.cache_miss || 0);
  const cacheHitPct = cacheTotal > 0
    ? Math.round((metrics.cache_hit / cacheTotal) * 100)
    : 0;

  const errorPct = metrics?.total_requests > 0
    ? Math.round((metrics.error_requests / metrics.total_requests) * 100)
    : 0;

  return (
    <div className="metrics-sidebar">
      <div className="metrics-header">
        <span className="metrics-title">Live Metrics</span>
        <button className="refresh-btn" onClick={onRefresh} title="Refresh">↻</button>
      </div>

      {!metrics ? (
        <div className="metrics-empty">Waiting for data…</div>
      ) : (
        <>
          <Section title="Requests">
            <Stat label="Total" value={metrics.total_requests} />
            <Stat label="Errors" value={metrics.error_requests} sub={`${errorPct}%`} warn={errorPct > 5} />
          </Section>

          <Section title="Cache">
            <Stat label="Hits" value={metrics.cache_hit} />
            <Stat label="Misses" value={metrics.cache_miss} />
            <div className="cache-bar-wrap">
              <div className="cache-bar-track">
                <div
                  className="cache-bar-fill"
                  style={{ width: `${cacheHitPct}%` }}
                />
              </div>
              <span className="cache-bar-label">{cacheHitPct}% hit rate</span>
            </div>
          </Section>

          <Section title="Fallbacks">
            <Stat label="Level 1" value={metrics.fallback_level1} warn={metrics.fallback_level1 > 0} />
            <Stat label="Level 2" value={metrics.fallback_level2} warn={metrics.fallback_level2 > 0} />
          </Section>

          <Section title="LLM Tokens">
            <Stat label="Prompt" value={metrics.prompt_tokens?.toLocaleString()} />
            <Stat label="Completion" value={metrics.completion_tokens?.toLocaleString()} />
            <Stat
              label="Total"
              value={((metrics.prompt_tokens || 0) + (metrics.completion_tokens || 0)).toLocaleString()}
            />
          </Section>

          <Section title="Documents">
            <Stat label="Ingested" value={metrics.docs_ingested} />
          </Section>
        </>
      )}

      <div className="metrics-footer">
        Auto-refreshes every 10s
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="metrics-section">
      <div className="metrics-section-title">{title}</div>
      {children}
    </div>
  );
}

function Stat({ label, value, sub, warn }) {
  return (
    <div className={`stat-row ${warn ? "stat-warn" : ""}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">
        {value ?? "—"}
        {sub && <span className="stat-sub"> ({sub})</span>}
      </span>
    </div>
  );
}
