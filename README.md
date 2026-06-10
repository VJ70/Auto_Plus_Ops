# Auto_Plus_Ops — Autonomous ML Pipeline Health Agent

<p align="center">
  <em>An autonomous ML pipeline health agent that monitors Arize Phoenix traces, reasons over them using Gemini, diagnoses root causes, and proposes remediation actions via a Human-in-the-Loop dashboard.</em>
</p>

---

## 📖 Overview

Auto_Plus_Ops is an intelligent, autonomous incident response system built for Machine Learning pipelines. It continuously monitors your production ML applications using **Arize Phoenix**, triages anomalous traces, and employs a chain of **Google Cloud ADK Agents** (powered by Gemini 2.0) to diagnose issues and propose concrete fixes. 

Crucially, Auto_Plus_Ops enforces a **Human-in-the-Loop (HITL)** constraint: no automated action is executed without human operator approval.

### ✨ Key Features
- **Continuous Monitoring**: Automatically tracks traces, spans, and errors via OpenTelemetry.
- **Multi-Agent Triage & Diagnosis**: Uses specialized ADK Agents to flag anomalies (e.g., high latency, token limits) and diagnose root causes.
- **Human-in-the-Loop Dashboard**: A React/Vite interface for operators to review, approve, or reject agent-proposed patches.
- **Feedback Loop**: Operator rejections are automatically logged back into Phoenix as dataset examples, improving future agent diagnostics.

## 🏗️ Architecture

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
    Backend -->|Feedback Loop| Phoenix
    end
```

## ⚙️ System Components

1. **Layer 0 — Monitored Pipeline**: A FastAPI app wrapping Gemini 2.0 Flash calls, instrumented with `openinference`. Emits OTel spans to Phoenix.
2. **Layer 1 — Arize Phoenix (MCP Partner)**: An MCP server exposing tools to interact with Phoenix (traces, spans, prompts, datasets).
3. **Layer 2 — Google Cloud ADK Agents**: 
   - **Triage Agent:** Polls `get-spans`, flags anomalous traces (latency, errors, rate limits).
   - **Diagnosis Agent:** Deep-dives into flagged traces to produce a root-cause analysis.
   - **Action Agent:** Maps diagnoses to concrete proposals (patch prompt, trigger retrain) and generates incident reports.
4. **Layer 3 — HITL Dashboard**: A React frontend and FastAPI backend where operators approve/reject the agent's proposed actions.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Docker** (for running Arize Phoenix)
- **Google Gemini API Key**

### 2. Environment Setup
Clone the repository and set up your environment variables:
```bash
cp .env.example .env
```
Fill in your `GOOGLE_API_KEY` inside the `.env` file.

### 3. Start Infrastructure
Start the Arize Phoenix instance using Docker:
```bash
docker run -d --name phoenix -p 6006:6006 arizephoenix/phoenix:latest
```

### 4. Run the Monitored Pipeline
In a new terminal window, start the instrumented ML pipeline:
```bash
cd pipeline
pip install -r requirements.txt
uvicorn app:app --port 8000
```
In another terminal, seed some initial traces (this script simulates normal traffic and anomalies):
```bash
cd pipeline
python app.py
```

### 5. Start the Dashboard (Backend & Frontend)
**Backend:**
```bash
cd dashboard/backend
pip install -r requirements.txt
uvicorn main:app --port 8001
```

**Frontend:**
```bash
cd dashboard/frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. Click **"Run Pipeline Now"** to trigger the agent workflow and view the diagnosed incidents.

---

## 📂 Project Structure

```text
Auto_Plus_Ops/
├── agent/                  # Google ADK Agents (Triage, Diagnosis, Action)
├── dashboard/
│   ├── backend/            # FastAPI backend for the HITL dashboard
│   └── frontend/           # React/Vite frontend UI
├── infra/                  # Dockerfiles and cloud configuration
├── pipeline/               # The monitored mock ML application
├── .env.example            # Template for environment variables
└── requirements.txt        # Root Python dependencies
```

## 📄 License
This project is licensed under the MIT License.
