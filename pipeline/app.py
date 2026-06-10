import os
from dotenv import load_dotenv
load_dotenv()

import random
import asyncio
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai

from phoenix.otel import register
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

# Init tracer
tracer_provider = register(
    project_name="auto_plus_ops-demo",
    endpoint=os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces"),
)

# Trace calls
GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)

# Init Gemini
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI(title="Auto_Plus_Ops Demo Pipeline", version="1.0.0")


class InferenceRequest(BaseModel):
    prompt: str
    inject_latency: bool = False
    inject_error: bool = False


class InferenceResponse(BaseModel):
    result: str
    latency_ms: float
    model_version: str


@app.post("/infer", response_model=InferenceResponse)
async def infer(req: InferenceRequest):
    if req.inject_error:
        raise HTTPException(status_code=500, detail="Simulated model error")

    if req.inject_latency:
        await asyncio.sleep(random.uniform(3.0, 6.0))

    start = time.perf_counter()
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=req.prompt
        )
        result_text = response.text
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise HTTPException(status_code=429, detail="Gemini API rate limit exceeded. Please wait a minute before retrying.")
        raise HTTPException(status_code=500, detail=str(e))
        
    elapsed_ms = (time.perf_counter() - start) * 1000

    return InferenceResponse(
        result=result_text,
        latency_ms=round(elapsed_ms, 2),
        model_version="gemini-2.0-flash-v1",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# Generate traces
if __name__ == "__main__":
    import httpx
    import time as _time

    PROMPTS = [
        "Summarize the benefits of CI/CD pipelines.",
        "What is retrieval-augmented generation?",
        "Explain gradient descent in one paragraph.",
        "List three best practices for prompt engineering.",
        "What is the difference between precision and recall?",
    ]

    print("Seeding 14 traces into Phoenix...")
    for i in range(14):
        prompt = PROMPTS[i % len(PROMPTS)]
        inject_latency = i >= 10
        r = httpx.post(
            "http://localhost:8000/infer",
            json={"prompt": prompt, "inject_latency": inject_latency},
            timeout=30,
        )
        print(f"  [{i+1}/14] status={r.status_code}  latency_injected={inject_latency}")
        _time.sleep(1.0)

    print("Done. Open Phoenix at http://localhost:6006")