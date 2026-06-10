import os
import json
import uuid
import httpx
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auto_plus_ops.dashboard")

app = FastAPI(title="Auto_Plus_Ops Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
pipeline_runs: list[dict] = []
incidents: dict[str, dict] = {}
operator_decisions: list[dict] = []


# Models
class OperatorDecision(BaseModel):
    incident_id: str
    decision: str
    operator_note: Optional[str] = None


class ManualTriggerRequest(BaseModel):
    user_id: str = "operator"


# Receive run
@app.post("/api/pipeline-run")
async def receive_pipeline_run(run: dict):
    pipeline_runs.insert(0, run)
    if len(pipeline_runs) > 100:
        pipeline_runs.pop()

    for incident in run.get("incidents", []):
        incident_id = incident.get("incident_id", str(uuid.uuid4()))
        incident["status"] = "pending"
        incidents[incident_id] = incident

    return {"received": True, "incident_count": len(run.get("incidents", []))}


# Endpoints
@app.get("/api/incidents")
async def list_incidents(status: Optional[str] = None):
    result = list(incidents.values())
    if status:
        result = [i for i in result if i.get("status") == status]
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    result.sort(key=lambda x: (sev_order.get(x.get("severity", "low"), 3), x.get("created_at", "")))
    return result


@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    if incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents[incident_id]


@app.get("/api/pipeline-runs")
async def list_pipeline_runs(limit: int = 20):
    return pipeline_runs[:limit]


@app.get("/api/stats")
async def get_stats():
    total = len(incidents)
    by_status = {}
    by_severity = {}
    for inc in incidents.values():
        s = inc.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1
        sv = inc.get("severity", "low")
        by_severity[sv] = by_severity.get(sv, 0) + 1
    return {
        "total_incidents": total,
        "by_status": by_status,
        "by_severity": by_severity,
        "total_runs": len(pipeline_runs),
        "last_run": pipeline_runs[0].get("timestamp") if pipeline_runs else None,
    }


# Decision endpoint
@app.post("/api/decide")
async def operator_decide(decision: OperatorDecision, background_tasks: BackgroundTasks):
    if decision.incident_id not in incidents:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = incidents[decision.incident_id]
    incident["status"] = "approved" if decision.decision == "approve" else "rejected"
    incident["operator_note"] = decision.operator_note
    incident["decided_at"] = datetime.now(timezone.utc).isoformat()

    log_entry = {
        "decision_id": str(uuid.uuid4()),
        "incident_id": decision.incident_id,
        "decision": decision.decision,
        "operator_note": decision.operator_note,
        "timestamp": incident["decided_at"],
        "incident_snapshot": incident,
    }
    operator_decisions.append(log_entry)

    if decision.decision == "approve":
        background_tasks.add_task(_execute_action, incident)

    # Log feedback
    background_tasks.add_task(_log_to_phoenix, log_entry)

    return {"success": True, "status": incident["status"]}


async def _execute_action(incident: dict):
    action_type = incident.get("action_type")
    payload = incident.get("action_payload", {})
    logger.info(f"Executing action: {action_type} for incident {incident.get('incident_id')}")

    if action_type == "patch_prompt":
        phoenix_url = os.getenv("PHOENIX_URL", "http://localhost:6006")
        prompt_id = payload.get("prompt_id")
        new_prompt = payload.get("new_prompt")
        if prompt_id and new_prompt:
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{phoenix_url}/v1/prompts/{prompt_id}",
                    json={"template": new_prompt},
                    timeout=10,
                )

    elif action_type == "trigger_retrain":
        mlflow_url = os.getenv("MLFLOW_URL", "http://localhost:5000")
        logger.info(f"Would trigger MLflow at {mlflow_url} with params: {payload}")

    elif action_type == "file_issue":
        github_token = os.getenv("GITHUB_TOKEN")
        github_repo = os.getenv("GITHUB_REPO")
        if github_token and github_repo:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.github.com/repos/{github_repo}/issues",
                    headers={"Authorization": f"Bearer {github_token}"},
                    json={
                        "title": payload.get("title", incident.get("title")),
                        "body": payload.get("body", incident.get("evidence")),
                        "labels": payload.get("labels", ["ml-ops"]),
                    },
                    timeout=10,
                )

    elif action_type == "dismiss":
        logger.info("Action dismissed by agent, no execution needed.")


async def _log_to_phoenix(log_entry: dict):
    phoenix_url = os.getenv("PHOENIX_URL", "http://localhost:6006")
    dataset_name = "auto_plus_ops-operator-feedback"

    example = {
        "input": {
            "trace_id": log_entry["incident_snapshot"].get("trace_id"),
            "root_cause": log_entry["incident_snapshot"].get("root_cause"),
            "suggested_action": log_entry["incident_snapshot"].get("action_type"),
        },
        "output": {
            "operator_decision": log_entry["decision"],
            "operator_note": log_entry.get("operator_note"),
        },
        "metadata": {
            "incident_id": log_entry["incident_id"],
            "severity": log_entry["incident_snapshot"].get("severity"),
            "decided_at": log_entry["timestamp"],
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            # Get dataset
            ds_resp = await client.post(
                f"{phoenix_url}/v1/datasets",
                json={"name": dataset_name},
                timeout=10,
            )
            dataset_id = ds_resp.json().get("id") or ds_resp.json().get("data", {}).get("id")

            if dataset_id:
                await client.post(
                    f"{phoenix_url}/v1/datasets/{dataset_id}/examples",
                    json={"examples": [example]},
                    timeout=10,
                )
                logger.info(f"Logged operator decision to Phoenix dataset {dataset_id}")
    except Exception as exc:
        logger.warning(f"Could not log to Phoenix: {exc}")


# Manual trigger
@app.post("/api/trigger-run")
async def trigger_manual_run(req: ManualTriggerRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_pipeline_background, req.user_id)
    return {"triggered": True, "user_id": req.user_id}


async def _run_pipeline_background(user_id: str):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from agent.orchestrator import run_pipeline
    result = run_pipeline(user_id=user_id)
    # Ingest
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8001/api/pipeline-run",
            json=result,
            timeout=60,
        )


@app.get("/health")
async def health():
    return {"status": "ok"}