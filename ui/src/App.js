import { useState, useEffect, useCallback } from "react";
import QueryPanel from "./components/QueryPanel";
import IngestPanel from "./components/IngestPanel";
import MetricsSidebar from "./components/MetricsSidebar";
import StatusBar from "./components/StatusBar";
import { fetchHealth, fetchRawMetrics, extractMetrics, listPrompts } from "./api/client";
import "./App.css";

const MEDUSA_LOGO = "data:image/jpeg;base64,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";

export default function App() {
  const [tab, setTab] = useState("query");
  const [apiStatus, setApiStatus] = useState("checking");
  const [metrics, setMetrics] = useState(null);
  const [promptVersions, setPromptVersions] = useState({
    versions: ["v1", "v2"],
    default: "v1",
  });

  const refreshMetrics = useCallback(async () => {
    try {
      const raw = await fetchRawMetrics();
      setMetrics(extractMetrics(raw));
    } catch {
      // Metrics are non-critical.
    }
  }, []);

  const checkApi = useCallback(async () => {
    try {
      await fetchHealth();
      setApiStatus("online");
    } catch {
      setApiStatus("offline");
    }
  }, []);

  useEffect(() => {
    checkApi();

    listPrompts()
      .then(setPromptVersions)
      .catch(() => {});

    refreshMetrics();

    const metricsTimer = setInterval(refreshMetrics, 10000);
    const healthTimer = setInterval(checkApi, 15000);

    return () => {
      clearInterval(metricsTimer);
      clearInterval(healthTimer);
    };
  }, [checkApi, refreshMetrics]);

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand-lockup">
          <img src={MEDUSA_LOGO} alt="Medusa" className="brand-logo" />
          <span className="brand-caption">RAG ENGINE</span>
        </div>

        <div className="sidebar-rule" />

        <div className="sidebar-label">WORKSPACE</div>
        <nav className="workspace-nav">
          <button
            className={`workspace-nav-item ${tab === "query" ? "active" : ""}`}
            onClick={() => setTab("query")}
          >
            <span className="nav-icon">⌁</span>
            <span>Ask Medusa</span>
            <span className="nav-arrow">↗</span>
          </button>

          <button
            className={`workspace-nav-item ${tab === "ingest" ? "active" : ""}`}
            onClick={() => setTab("ingest")}
          >
            <span className="nav-icon">＋</span>
            <span>Knowledge Base</span>
            <span className="nav-arrow">↗</span>
          </button>
        </nav>

        <div className="sidebar-spacer" />

        <div className="connection-card">
          <div className="connection-head">
            <span>ENGINE STATUS</span>
            <StatusBar status={apiStatus} />
          </div>
          <div className="connection-copy">
            {apiStatus === "online"
              ? "Backend is reachable and ready for queries."
              : apiStatus === "checking"
                ? "Checking the Medusa API connection…"
                : "Backend is unreachable. Start the API and try again."}
          </div>
          <button className="connection-refresh" onClick={checkApi}>
            Refresh connection
          </button>
        </div>

        <div className="sidebar-footer">
          <span>MEDUSA © 2026</span>
          <span>KNOWLEDGE IS POWER.</span>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <div className="eyebrow">MEDUSA / LOCAL RAG SYSTEM</div>
            <h1>{tab === "query" ? "Knowledge, unlocked." : "Build the knowledge base."}</h1>
          </div>
          <div className="topbar-status">
            <span className="status-kicker">API</span>
            <StatusBar status={apiStatus} />
          </div>
        </header>

        <div className="hero-strip">
          <div className="hero-copy">
            <span className="hero-index">01 — {tab === "query" ? "QUERY" : "INGEST"}</span>
            <p>
              {tab === "query"
                ? "Retrieve context from your documents, route it through the configured prompt, and inspect the result."
                : "Add PDFs, text, or Markdown to the vector store and make them available to Medusa immediately."}
            </p>
          </div>
          <div className="hero-mark" aria-hidden="true">
            <span>Μ</span>
          </div>
        </div>

        <div className="content-grid">
          <main className="main-content">
            {tab === "query" ? (
              <QueryPanel
                promptVersions={promptVersions}
                onQueryComplete={refreshMetrics}
              />
            ) : (
              <IngestPanel onIngestComplete={refreshMetrics} />
            )}
          </main>

          <aside className="metrics-panel">
            <MetricsSidebar metrics={metrics} onRefresh={refreshMetrics} />
          </aside>
        </div>

        <footer className="workspace-footer">
          <span>MEDUSA / RAG API</span>
          <span>CONTEXT IS EVERYTHING.</span>
          <span>ENGINEERED BY SAGAR PRAJAPATI</span>
        </footer>
      </section>
    </div>
  );
}