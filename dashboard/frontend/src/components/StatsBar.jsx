export default function StatsBar({ stats }) {
  if (!stats) return null;

  const cards = [
    { label: "Total Incidents", value: stats.total_incidents, gradient: true },
    { label: "Pending", value: stats.by_status?.pending || 0, color: "var(--status-pending)" },
    { label: "Approved", value: stats.by_status?.approved || 0, color: "var(--status-approved)" },
    { label: "Rejected", value: stats.by_status?.rejected || 0, color: "var(--status-rejected)" },
  ];

  return (
    <div className="stats-bar">
      {cards.map((c) => (
        <div key={c.label} className="glass-card stat-card fade-in">
          <div
            className={`stat-value ${c.gradient ? "gradient" : ""}`}
            style={c.color ? { color: c.color } : undefined}
          >
            {c.value}
          </div>
          <div className="stat-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
