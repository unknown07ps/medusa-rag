import { useState, useRef } from "react";
import { ingestFile, ingestText } from "../api/client";

export default function IngestPanel({ onIngestComplete }) {
  const [mode, setMode] = useState("file");
  const [text, setText] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [ingested, setIngested] = useState([]);
  const fileRef = useRef();

  async function handleIngest() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let data;
      if (mode === "file") {
        if (!file) throw new Error("Select a file first.");
        data = await ingestFile(file);
      } else {
        if (text.trim().length < 10) throw new Error("Text too short.");
        data = await ingestText({ text: text.trim(), source_name: sourceName || "inline_text" });
      }
      setResult(data);
      setIngested((prev) => [{ ...data, ts: new Date() }, ...prev].slice(0, 20));
      setFile(null);
      setText("");
      setSourceName("");
      if (fileRef.current) fileRef.current.value = "";
      onIngestComplete();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Ingest Documents</h2>
        <p className="panel-desc">Upload a PDF/TXT/MD file or paste text directly into the vector store.</p>
      </div>

      <div className="mode-tabs">
        <button
          className={`mode-tab ${mode === "file" ? "active" : ""}`}
          onClick={() => setMode("file")}
        >
          Upload File
        </button>
        <button
          className={`mode-tab ${mode === "text" ? "active" : ""}`}
          onClick={() => setMode("text")}
        >
          Paste Text
        </button>
      </div>

      {mode === "file" ? (
        <div className="file-zone" onClick={() => fileRef.current?.click()}>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.txt,.md"
            style={{ display: "none" }}
            onChange={(e) => setFile(e.target.files[0] || null)}
          />
          {file ? (
            <div className="file-selected">
              <span className="file-icon">📄</span>
              <span className="file-name">{file.name}</span>
              <span className="file-size">({(file.size / 1024).toFixed(1)} KB)</span>
            </div>
          ) : (
            <div className="file-placeholder">
              <span className="file-icon-lg">⬆</span>
              <span>Click to select a PDF, TXT, or MD file</span>
              <span className="file-limit">Max 20 MB</span>
            </div>
          )}
        </div>
      ) : (
        <div className="text-ingest">
          <input
            className="source-input"
            placeholder="Source name (optional)"
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
          />
          <textarea
            className="query-input"
            placeholder="Paste your document text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
          />
        </div>
      )}

      <button
        className={`submit-btn ${loading ? "loading" : ""}`}
        onClick={handleIngest}
        disabled={loading}
      >
        {loading ? (
          <span className="spinner-row"><span className="spinner" /> Ingesting...</span>
        ) : "Ingest"}
      </button>

      {error && <div className="error-box">{error}</div>}

      {result && (
        <div className="result-box">
          <div className="result-meta">
            <div className="meta-badge">
              <span className="meta-label">Doc ID</span>
              <span className="meta-value mono">{result.doc_id?.slice(0, 12)}…</span>
            </div>
            <div className="meta-badge">
              <span className="meta-label">Chunks</span>
              <span className="meta-value">{result.chunk_count}</span>
            </div>
            <div className="meta-badge">
              <span className="meta-label">File</span>
              <span className="meta-value">{result.filename}</span>
            </div>
          </div>
          <div className="success-msg">Document ingested successfully and ready to query.</div>
        </div>
      )}

      {ingested.length > 0 && (
        <div className="history">
          <div className="history-title">Ingested this session</div>
          {ingested.map((d, i) => (
            <div key={i} className="history-item">
              <span className="history-q">{d.filename}</span>
              <span className="meta-badge" style={{ marginLeft: "auto" }}>
                <span className="meta-value">{d.chunk_count} chunks</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
