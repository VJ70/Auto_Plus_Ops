import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import StatsBar from "./components/StatsBar";
import IncidentCard from "./components/IncidentCard";
import IncidentDetail from "./components/IncidentDetail";
import PipelineTimeline from "./components/PipelineTimeline";
import TriggerButton from "./components/TriggerButton";

const API = "/api";

export default function App() {
  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState(null);
  const [runs, setRuns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchAll = useCallback(async () => {
    try {
      const [incRes, statsRes, runsRes] = await Promise.all([
        fetch(`${API}/incidents`),
        fetch(`${API}/stats`),
        fetch(`${API}/pipeline-runs?limit=10`),
      ]);
      setIncidents(await incRes.json());
      setStats(await statsRes.json());
      setRuns(await runsRes.json());
    } catch (err) {
      console.error("Fetch error:", err);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const handleDecide = async (incidentId, decision, note) => {
    setLoading(true);
    try {
      await fetch(`${API}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          incident_id: incidentId,
          decision,
          operator_note: note || null,
        }),
      });
      await fetchAll();
      setSelected((prev) =>
        prev && prev.incident_id === incidentId
          ? { ...prev, status: decision === "approve" ? "approved" : "rejected" }
          : prev
      );
    } catch (err) {
      console.error("Decision error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleTrigger = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/trigger-run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "operator" }),
      });
      setTimeout(fetchAll, 3000);
    } catch (err) {
      console.error("Trigger error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <Header />
      <StatsBar stats={stats} />
      <div className="main-grid">
        <div>
          <h2 className="section-title">Incidents</h2>
          {incidents.length === 0 ? (
            <div className="empty-state glass-card">
              <div className="empty-state-icon">🛡️</div>
              <p>No incidents yet. Pipeline is healthy.</p>
            </div>
          ) : (
            <div className="incident-list">
              {incidents.map((inc, i) => (
                <IncidentCard
                  key={inc.incident_id || i}
                  incident={inc}
                  active={selected?.incident_id === inc.incident_id}
                  onClick={() => setSelected(inc)}
                />
              ))}
            </div>
          )}
          <PipelineTimeline runs={runs} />
          <TriggerButton onTrigger={handleTrigger} loading={loading} />
        </div>
        <div>
          <IncidentDetail
            incident={selected}
            onDecide={handleDecide}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}
