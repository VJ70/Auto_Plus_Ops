# Auto_Plus_Ops — Autonomous ML Pipeline Health Agent

<p align="center">
 An autonomous ML pipeline health agent that reads traces and experiments from Arize Phoenix, reasons over them with Gemini 3, diagnoses root causes, and proposes actions — which a human operator approves before anything executes.
</p>

## Architecture

```mermaid
flowchart TD
    subgraph Layer 0: Monitored Pipeline
    App[FastAPI App] -->|OTel Spans| Phoenix[(Arize Phoenix)]
    end

    subgraph Layer 1: Phoenix MCP
    Phoenix -->|get-spans, get-traces| MCP[MCP Server]
    Phoenix -->|experiments, datasets| MCP
    end

    subgraph Layer 2: ADK Agents (Google Cloud)
    MCP <--> Triage[Triage Agent]
    MCP <--> Diagnosis[Diagnosis Agent]
    MCP <--> Action[Action Agent]
    
    Triage -->|Flagged Traces| Diagnosis
    Diagnosis -->|Root Causes| Action
    Action -->|Incident Reports| Backend
    end
    
    subgraph Layer 3: Dashboard
    Backend[FastAPI Backend] <--> DB[(In-Memory State)]
    Backend <--> Frontend[React/Vite UI]
    Frontend -->|Approve/Reject| Backend
    Backend -->|Feedback Loop (Add Dataset)| Phoenix
    Backend -->|Execute Patch/Retrain| Integrations[GitHub/MLflow]
    end

    Cron((Cloud Scheduler)) -->|Pub/Sub| Triage
```

## System Components

1. **Layer 0 — The Monitored Pipeline:** A FastAPI app wrapping Gemini 2.0 Flash calls, instrumented with `openinference-instrumentation`. Every model call emits OTel spans to Phoenix automatically.
2. **Layer 1 — Arize Phoenix (MCP Partner):** An MCP server exposing tools to interact with Phoenix (traces, spans, prompts, datasets, experiments).
3. **Layer 2 — Google Cloud Agent Builder (ADK):** Three chained agents sharing context via Agent Engine Session Memory:
   - **Triage Agent:** Runs on a schedule, polls `get-spans`, flags anomalous traces based on latency, errors, or token counts.
   - **Diagnosis Agent:** Deep-dives into flagged traces (`get-trace`), compares against baseline experiments (`list-experiments-for-dataset`), and produces a root-cause JSON.
   - **Action Agent:** Maps diagnoses to concrete proposals (patch prompt, trigger retrain, file issue, dismiss) and generates structured incident reports.
4. **Layer 3 — Human-in-the-Loop Dashboard:** A React frontend and FastAPI backend where an operator can approve or reject the agent's proposed actions. **Rejections are logged back to Phoenix as a dataset example**, creating a continuous self-improvement loop.

## Quick Start

### 1. Prerequisites
- Python 3.12+
- Node.js 20+
- A running Arize Phoenix instance (`docker run -p 6006:6006 arizeai/phoenix:latest`)
- A Google API Key (for Gemini)

### 2. Environment Setup
Copy the template and fill in your keys:
```bash
cp .env.example .env
```

### 3. Run the Monitored Pipeline
In **Terminal 1** — start the server:
```bash
cd pipeline
pip install -r requirements.txt
uvicorn app:app --port 8000
```

In **Terminal 2** — seed 60 traces (last 15 with anomalies):
```bash
cd pipeline
python app.py
```

### 4. Run the Dashboard Backend & Orchestrator
```bash
cd dashboard/backend
pip install -r requirements.txt
uvicorn main:app --port 8001
```
*(You can also trigger a manual agent run by executing `python -m agent.orchestrator` from the project root).*

### 5. Run the Dashboard Frontend
```bash
cd dashboard/frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. Click **"Run Pipeline Now"** to trigger the agent workflow.


## License
MIT
