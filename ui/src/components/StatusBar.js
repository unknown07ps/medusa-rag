export default function StatusBar({ status }) {
  const map = {
    checking: { dot: "dot-yellow", label: "Checking…" },
    online:   { dot: "dot-green",  label: "API Online" },
    offline:  { dot: "dot-red",    label: "API Offline" },
  };
  const { dot, label } = map[status] || map.checking;
  return (
    <div className="status-bar">
      <span className={`status-dot ${dot}`} />
      <span className="status-label">{label}</span>
    </div>
  );
}
