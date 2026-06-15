import { useState, useEffect, useCallback } from "react";
import QueryPanel from "./components/QueryPanel";
import IngestPanel from "./components/IngestPanel";
import MetricsSidebar from "./components/MetricsSidebar";
import StatusBar from "./components/StatusBar";
import { fetchHealth, fetchRawMetrics, extractMetrics, listPrompts } from "./api/client";
import "./App.css";

export default function App() {
  const [tab, setTab] = useState("query");
  const [apiStatus, setApiStatus] = useState("checking");
  const [metrics, setMetrics] = useState(null);
  const [promptVersions, setPromptVersions] = useState({ versions: ["v1", "v2"], default: "v1" });

  const refreshMetrics = useCallback(async () => {
    try {
      const raw = await fetchRawMetrics();
      setMetrics(extractMetrics(raw));
    } catch {
      // metrics are non-critical
    }
  }, []);

  useEffect(() => {
    fetchHealth()
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));

    listPrompts()
      .then(setPromptVersions)
      .catch(() => {});

    refreshMetrics();
    const id = setInterval(refreshMetrics, 10000);
    return () => clearInterval(id);
  }, [refreshMetrics]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-left">
          <span className="logo">
            <span className="logo-m">M</span>edusa
          </span>
          <span className="logo-sub">RAG API</span>
        </div>
        <nav className="nav">
          <button
            className={`nav-btn ${tab === "query" ? "active" : ""}`}
            onClick={() => setTab("query")}
          >
            Query
          </button>
          <button
            className={`nav-btn ${tab === "ingest" ? "active" : ""}`}
            onClick={() => setTab("ingest")}
          >
            Ingest
          </button>
        </nav>
        <StatusBar status={apiStatus} />
      </header>

      <div className="body">
        <main className="main">
          {tab === "query" ? (
            <QueryPanel
              promptVersions={promptVersions}
              onQueryComplete={refreshMetrics}
            />
          ) : (
            <IngestPanel onIngestComplete={refreshMetrics} />
          )}
        </main>
        <aside className="sidebar">
          <MetricsSidebar metrics={metrics} onRefresh={refreshMetrics} />
        </aside>
      </div>
    </div>
  );
}
