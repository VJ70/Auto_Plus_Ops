export default function TriggerButton({ onTrigger, loading }) {
  return (
    <div className="trigger-section">
      <button
        className="btn-trigger"
        onClick={onTrigger}
        disabled={loading}
      >
        {loading && <span className="spinner" />}
        {loading ? "Running Pipeline…" : "⚡ Run Pipeline Now"}
      </button>
    </div>
  );
}
