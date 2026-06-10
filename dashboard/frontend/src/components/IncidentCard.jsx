export default function IncidentCard({ incident, active, onClick }) {
  const sev = incident.severity || "low";
  const status = incident.status || "pending";

  return (
    <div
      className={`glass-card incident-card fade-in ${active ? "active" : ""}`}
      data-severity={sev}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <div className="incident-header">
        <span className="incident-title">{incident.title || "Untitled Incident"}</span>
        <span className={`badge badge-${sev}`}>{sev}</span>
        <span className={`badge badge-${status}`}>{status}</span>
      </div>
      <div className="incident-meta">
        <span>🔗 {incident.trace_id ? incident.trace_id.slice(0, 12) + "…" : "—"}</span>
        <span>⚡ {incident.action_type || "—"}</span>
        <span>🎯 {incident.confidence != null ? (incident.confidence * 100).toFixed(0) + "%" : "—"}</span>
        {incident.created_at && (
          <span>{new Date(incident.created_at).toLocaleTimeString()}</span>
        )}
      </div>
    </div>
  );
}
