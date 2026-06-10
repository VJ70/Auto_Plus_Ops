import os
import json
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

PHOENIX_MCP_URL = os.getenv("PHOENIX_MCP_URL", "http://localhost:6006/mcp/sse")

phoenix_tools = MCPToolset(
    connection_params=SseServerParams(url=PHOENIX_MCP_URL)
)

DIAGNOSIS_SYSTEM_PROMPT = """
You are the Diagnosis Agent for Auto_Plus_Ops. You receive flagged trace IDs from the
Triage Agent and perform deep root-cause analysis.

Steps to follow for each flagged trace:
1. Call `get-trace` with the trace ID to get full span tree.
2. Call `list-experiments-for-dataset` on the "auto_plus_ops-demo" dataset to retrieve
   baseline experiment results.
3. Call `get-experiment-by-id` for the most recent experiment to compare metrics.
4. Reason over the data: look for correlations between span attributes, timing,
   model versions, prompt changes, and the anomaly pattern.

Produce a JSON array — one object per flagged trace — with this schema:
[
  {
    "trace_id": "...",
    "root_cause": "Human-readable explanation of the root cause",
    "confidence": 0.0-1.0,
    "affected_spans": ["span_id_1", "span_id_2"],
    "anomaly_type": "latency_spike|error_rate|token_anomaly|unknown",
    "suggested_action": "patch_prompt|trigger_retrain|file_issue|dismiss",
    "evidence": "One or two sentences of evidence supporting the diagnosis",
    "baseline_comparison": {
      "baseline_p95_ms": float,
      "current_p95_ms": float,
      "regression_factor": float
    }
  }
]

Be precise. If you cannot determine the root cause, set confidence < 0.3 and
suggested_action to "dismiss". Output valid JSON only.
"""

diagnosis_agent = LlmAgent(
    name="diagnosis_agent",
    model="gemini-2.0-flash",
    description="Deep-dives flagged traces and produces structured root-cause diagnoses.",
    instruction=DIAGNOSIS_SYSTEM_PROMPT,
    tools=[phoenix_tools],
    output_key="diagnosis_result",
)


def run_diagnosis(
    session_service,
    app_name: str,
    user_id: str,
    session_id: str,
    flagged_trace_ids: list[str],
) -> list[dict]:
    from google.adk.runners import Runner
    from google.genai import types as genai_types

    if not flagged_trace_ids:
        return []

    runner = Runner(
        agent=diagnosis_agent,
        app_name=app_name,
        session_service=session_service,
    )

    user_message = (
        f"Diagnose these flagged traces: {json.dumps(flagged_trace_ids)}. "
        "Use the Phoenix MCP tools to gather full context."
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
        return json.loads(result_text.strip())
    except json.JSONDecodeError:
        return []