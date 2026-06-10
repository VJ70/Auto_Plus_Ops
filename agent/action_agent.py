import os
import json
import uuid
from datetime import datetime, timezone
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

PHOENIX_MCP_URL = os.getenv("PHOENIX_MCP_URL", "http://localhost:6006/mcp/sse")

phoenix_tools = MCPToolset(
    connection_params=SseServerParams(url=PHOENIX_MCP_URL)
)

ACTION_SYSTEM_PROMPT = """
You are the Action Agent for Auto_Plus_Ops. You receive structured diagnosis results
and convert them into actionable incident reports for a human operator.

For each diagnosis entry:
- Map suggested_action to a concrete, human-readable action plan:
    - "patch_prompt"    -> "Update the system prompt in Phoenix Prompt Management
                           to reduce latency. Suggested revision: [specific change]."
    - "trigger_retrain" -> "Trigger MLflow pipeline run with config: {checkpoint: latest,
                           dataset: auto_plus_ops-demo, epochs: 5}."
    - "file_issue"      -> "Create GitHub issue: 'Performance regression in [span_name]'
                           with labels: bug, ml-ops, priority:high."
    - "dismiss"         -> "No action needed. Log as noise and continue monitoring."

Produce a single JSON object per diagnosis:
{
  "incident_id": "<uuid4>",
  "created_at": "<ISO-8601 UTC>",
  "severity": "critical|high|medium|low",
  "title": "Short incident title (< 60 chars)",
  "trace_id": "...",
  "root_cause": "...",
  "confidence": 0.0-1.0,
  "action_type": "patch_prompt|trigger_retrain|file_issue|dismiss",
  "action_plan": "Detailed step-by-step action description",
  "action_payload": {
    // action-type-specific data the backend will use to execute:
    // For patch_prompt: {"prompt_id": "...", "new_prompt": "..."}
    // For trigger_retrain: {"pipeline": "mlflow", "params": {...}}
    // For file_issue: {"title": "...", "body": "...", "labels": [...]}
    // For dismiss: {}
  },
  "evidence": "...",
  "baseline_comparison": {...}
}

Severity mapping:
- regression_factor > 3 or error_rate anomaly -> critical
- regression_factor 2-3 -> high
- regression_factor 1.5-2 -> medium
- regression_factor < 1.5 or dismiss -> low

Output a JSON array of incident objects and nothing else.
"""

action_agent = LlmAgent(
    name="action_agent",
    model="gemini-2.0-flash",
    description="Converts diagnoses into structured incident reports for human review.",
    instruction=ACTION_SYSTEM_PROMPT,
    tools=[phoenix_tools],
    output_key="action_result",
)


def run_action(
    session_service,
    app_name: str,
    user_id: str,
    session_id: str,
    diagnoses: list[dict],
) -> list[dict]:
    from google.adk.runners import Runner
    from google.genai import types as genai_types

    if not diagnoses:
        return []

    runner = Runner(
        agent=action_agent,
        app_name=app_name,
        session_service=session_service,
    )

    user_message = (
        "Build incident reports for these diagnoses:\n"
        + json.dumps(diagnoses, indent=2)
    )

    result_text = ""
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        ),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    result_text += part.text

    try:
        incidents = json.loads(result_text.strip())
        # Ensure every incident has a fresh UUID and timestamp
        for inc in incidents:
            inc.setdefault("incident_id", str(uuid.uuid4()))
            inc.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        return incidents
    except json.JSONDecodeError:
        return []