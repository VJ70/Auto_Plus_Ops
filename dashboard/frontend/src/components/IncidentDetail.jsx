import { useState } from "react";

export default function IncidentDetail({ incident, onDecide, loading }) {
  const [note, setNote] = useState("");

  if (!incident) {
    return (
      <div className="glass-card detail-panel detail-empty">
        <div className="detail-empty-icon">📋</div>
        <p>Select an incident to view details</p>
      </div>
    );
  }

  const isPending = incident.status === "pending";
  const baseline = incident.baseline_comparison || {};

  return (
    <div className="glass-card detail-panel fade-in" key={incident.incident_id}>
      <div className="incident-header" style={{ marginBottom: 16 }}>
        <span className={`badge badge-${incident.severity || "low"}`}>
          {incident.severity || "low"}
        </span>
        <span className={`badge badge-${incident.status || "pending"}`}>
          {incident.status || "pending"}
        </span>
      </div>

      <h3 className="detail-title">{incident.title || "Incident"}</h3>

      <div className="detail-section">
        <div className="detail-label">Root Cause</div>
        <div className="detail-value">{incident.root_cause || "—"}</div>
      </div>

      <div className="detail-section">
        <div className="detail-label">Evidence</div>
        <div className="detail-evidence">{incident.evidence || "No evidence provided."}</div>
      </div>

      <div className="detail-section">
        <div className="detail-label">Action Plan</div>
        <div className="detail-value">{incident.action_plan || "—"}</div>
      </div>

      {(baseline.baseline_p95_ms || baseline.current_p95_ms || baseline.regression_factor) && (
        <div className="detail-section">
          <div className="detail-label">Baseline Comparison</div>
          <div className="baseline-grid">
            <div className="baseline-item">
              <div className="baseline-number" style={{ color: "var(--sev-low)" }}>
                {baseline.baseline_p95_ms != null ? `${baseline.baseline_p95_ms}ms` : "—"}
              </div>
              <div className="baseline-label">Baseline P95</div>
            </div>
            <div className="baseline-item">
              <div className="baseline-number" style={{ color: "var(--sev-critical)" }}>
                {baseline.current_p95_ms != null ? `${baseline.current_p95_ms}ms` : "—"}
              </div>
              <div className="baseline-label">Current P95</div>
            </div>
            <div className="baseline-item">
              <div className="baseline-number" style={{ color: "var(--accent-violet)" }}>
                {baseline.regression_factor != null ? `${baseline.regression_factor}×` : "—"}
              </div>
              <div className="baseline-label">Regression</div>
            </div>
          </div>
        </div>
      )}

      <div className="detail-section">
        <div className="detail-label">Trace ID</div>
        <div className="detail-value" style={{ fontFamily: "monospace", fontSize: 12 }}>
          {incident.trace_id || "—"}
        </div>
      </div>

      <div className="detail-section">
        <div className="detail-label">Confidence</div>
        <div className="detail-value">
          {incident.confidence != null ? `${(incident.confidence * 100).toFixed(1)}%` : "—"}
        </div>
      </div>

      {isPending && (
        <>
          <div className="detail-section">
            <div className="detail-label">Operator Note (optional)</div>
            <textarea
              className="note-input"
              placeholder="Add a note for the decision log..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
          <div className="action-buttons">
            <button
              className="btn btn-approve"
              disabled={loading}
              onClick={() => onDecide(incident.incident_id, "approve", note)}
            >
              ✓ Approve
            </button>
            <button
              className="btn btn-reject"
              disabled={loading}
              onClick={() => onDecide(incident.incident_id, "reject", note)}
            >
              ✕ Reject
            </button>
          </div>
        </>
      )}

      {!isPending && incident.operator_note && (
        <div className="detail-section">
          <div className="detail-label">Operator Note</div>
          <div className="detail-evidence">{incident.operator_note}</div>
        </div>
      )}
    </div>
  );
}
