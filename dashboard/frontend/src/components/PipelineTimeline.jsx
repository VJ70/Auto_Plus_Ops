export default function PipelineTimeline({ runs }) {
  if (!runs || runs.length === 0) return null;

  return (
    <div className="timeline">
      <h2 className="section-title">Pipeline Runs</h2>
      <div className="timeline-list">
        {runs.map((run, i) => {
          const status = run.status || "healthy";
          const incidentCount = (run.incidents || []).length;
          const ts = run.timestamp
            ? new Date(run.timestamp).toLocaleString()
            : "—";

          return (
            <div key={run.run_id || i} className="glass-card timeline-item fade-in">
              <span className={`timeline-dot ${status}`} />
              <span className="timeline-ts">{ts}</span>
              <span className={`timeline-status ${status}`}>
                {status === "healthy" ? "Healthy" : "Anomalies Detected"}
              </span>
              {incidentCount > 0 && (
                <span className="timeline-incidents">
                  {incidentCount} incident{incidentCount > 1 ? "s" : ""}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
