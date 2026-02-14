import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from genai_agent.src.engine import ArgusEngine
import json
import asyncio
from pathlib import Path

app = FastAPI()
engine = None

# Ensure directories exist
UPLOAD_DIR = Path("genai_agent/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="genai_agent/src/static"), name="static")

@app.on_event("startup")
async def startup_event():
    global engine
    try:
        engine = ArgusEngine()
    except Exception as e:
        print(f"Engine initialization error: {e}")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("genai_agent/src/static/index.html", "r") as f:
        return f.read()

import time

@app.post("/chat")
async def chat(message: str = Form(...), file_path: str = Form(None)):
    global engine
    start_time = time.time()

    if not engine:
        # Try re-initializing if it failed at startup
        try:
            engine = ArgusEngine()
        except Exception:
            return {"error": "Engine not initialized. Check API Key."}

    query = message
    if file_path:
        print(f"[*] Analyzing CSV: {file_path}")
        query = f"Using this data: {file_path}. Question: {message}"

    def generate():
        print(f"[*] Querying LLM: {message[:50]}...")
        first_chunk = True
        for chunk in engine.stream_query(query):
            if first_chunk:
                print(f"[*] First chunk received in {time.time() - start_time:.2f}s")
                first_chunk = False
            yield chunk
        print(f"[*] Total response time: {time.time() - start_time:.2f}s")

    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/run-simulation")
async def run_simulation():
    async def run_scripts():
        scripts = [
            ("Fraud Detection Demo", ["bash", "fraud_detection/demo/run_demo.sh"]),
            ("Real-Time Inference", ["python", "realtime_ml_system/demo/online_inference.py"]),
            ("ML Platform Pipeline", ["python", "ml_platform/demo/pipeline.py"])
        ]

        for name, cmd in scripts:
            yield f"\n>>> Starting {name}...\n"
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                yield line.decode()

            await process.wait()
            yield f">>> {name} completed.\n"

        yield "\n[SUCCESS] All systems verified. Metrics updated.\n"

    return StreamingResponse(run_scripts(), media_type="text/plain")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": str(file_path)}

@app.get("/metrics")
async def get_metrics():
    # Load metrics from all systems
    metrics = {
        "ml_platform": {},
        "realtime_ml": {}
    }

    ml_metrics_path = Path("ml_platform/demo/results/metrics.json")
    if ml_metrics_path.exists():
        with open(ml_metrics_path, "r") as f:
            metrics["ml_platform"] = json.load(f)

    ml_val_path = Path("ml_platform/demo/results/validation_report.json")
    if ml_val_path.exists():
        with open(ml_val_path, "r") as f:
            metrics["ml_platform"]["validation"] = json.load(f)

    # Try to get latest realtime stats
    rt_metrics_path = Path("realtime_ml_system/demo/results/summary.json")
    if rt_metrics_path.exists():
         with open(rt_metrics_path, "r") as f:
            metrics["realtime_ml"] = json.load(f)

    return metrics

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
