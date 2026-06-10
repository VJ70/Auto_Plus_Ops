import os
import uuid
import logging
from datetime import datetime, timezone

from google.adk.sessions import InMemorySessionService
# Prod: VertexAiSessionService
# from google.adk.sessions import VertexAiSessionService

from agent.triage_agent import run_triage
from agent.diagnosis_agent import run_diagnosis
from agent.action_agent import run_action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto_plus_ops.orchestrator")

APP_NAME = "auto_plus_ops"


def run_pipeline(user_id: str = "system") -> dict:
    session_service = InMemorySessionService()
    session_id = f"session-{uuid.uuid4().hex[:8]}"
    run_ts = datetime.now(timezone.utc).isoformat()

    # Create session
    session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    logger.info(f"[{session_id}] Pipeline run started at {run_ts}")

    # Stage 1: Triage
    logger.info(f"[{session_id}] Running Triage Agent...")
    triage_result = run_triage(session_service, APP_NAME, user_id, session_id)
    logger.info(
        f"[{session_id}] Triage complete: anomalies={triage_result.get('anomalies_found')}, "
        f"flagged={len(triage_result.get('flagged_trace_ids', []))}"
    )

    if not triage_result.get("anomalies_found"):
        logger.info(f"[{session_id}] Pipeline healthy — no action needed.")
        return {
            "run_id": session_id,
            "timestamp": run_ts,
            "status": "healthy",
            "triage": triage_result,
            "diagnoses": [],
            "incidents": [],
        }

    # Stage 2: Diagnosis
    logger.info(f"[{session_id}] Running Diagnosis Agent...")
    diagnoses = run_diagnosis(
        session_service,
        APP_NAME,
        user_id,
        session_id,
        triage_result["flagged_trace_ids"],
    )
    logger.info(f"[{session_id}] Diagnosis complete: {len(diagnoses)} diagnoses produced.")

    # Stage 3: Action
    logger.info(f"[{session_id}] Running Action Agent...")
    incidents = run_action(session_service, APP_NAME, user_id, session_id, diagnoses)
    logger.info(f"[{session_id}] Action complete: {len(incidents)} incident reports generated.")

    return {
        "run_id": session_id,
        "timestamp": run_ts,
        "status": "anomalies_detected",
        "triage": triage_result,
        "diagnoses": diagnoses,
        "incidents": incidents,
    }


# Pub/Sub entry
def pubsub_handler(event, context):
    import httpx

    result = run_pipeline()

    # Update dashboard
    dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8001")
    try:
        httpx.post(
            f"{dashboard_url}/api/pipeline-run",
            json=result,
            timeout=10,
        )
    except Exception as exc:
        logger.warning(f"Could not push to dashboard: {exc}")

    return result


# Local testing
if __name__ == "__main__":
    import json
    result = run_pipeline(user_id="cli-test")
    print(json.dumps(result, indent=2))