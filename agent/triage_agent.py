import os
import json
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseServerParams

# MCP connection
PHOENIX_MCP_URL = os.getenv("PHOENIX_MCP_URL", "http://localhost:6006/mcp/sse")

phoenix_tools = MCPToolset(
    connection_params=SseServerParams(url=PHOENIX_MCP_URL)
)

# System prompt
TRIAGE_SYSTEM_PROMPT = """
You are the Triage Agent for Auto_Plus_Ops, an autonomous ML pipeline health monitor.

Your job:
1. Call `get-spans` for the last 15 minutes on the "auto_plus_ops-demo" project.
2. Call `list-traces` to get trace metadata.
3. For each trace, evaluate:
   - Latency: flag if p95 > 2000 ms or any span > 5000 ms
   - Error rate: flag if error_count / total_spans > 0.05
   - Token anomaly: flag if token_count > 3x the rolling average
4. Output a JSON object with this exact schema:
   {
     "anomalies_found": boolean,
     "flagged_trace_ids": ["trace_id_1", ...],
     "summary": "One-sentence description of what you found",
     "healthy_span_count": int,
     "flagged_span_count": int
   }

If no anomalies, set anomalies_found=false and flagged_trace_ids=[].
Always output valid JSON and nothing else.
"""

triage_agent = LlmAgent(
    name="triage_agent",
    model="gemini-2.0-flash",
    description="Polls Phoenix spans and flags anomalous traces for diagnosis.",
    instruction=TRIAGE_SYSTEM_PROMPT,
    tools=[phoenix_tools],
    output_key="triage_result",
)


def run_triage(session_service, app_name: str, user_id: str, session_id: str) -> dict:
    from google.adk.runners import Runner
    from google.genai import types as genai_types

    runner = Runner(
        agent=triage_agent,
        app_name=app_name,
        session_service=session_service,
    )

    result_text = ""
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part(text="Run triage now. Check the last 15 minutes.")],
        ),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    result_text += part.text

    try:
        return json.loads(result_text.strip())
    except json.JSONDecodeError:
        return {
            "anomalies_found": False,
            "flagged_trace_ids": [],
            "summary": "Triage parsing error",
            "healthy_span_count": 0,
            "flagged_span_count": 0,
        }