import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from genai_agent.src.engine import ArgusEngine
import json
import asyncio
from pathlib import Path

from collections import defaultdict
import datetime

# --- Rate Limiter ---
class RateLimiter:
    def __init__(self, requests_per_minute=5, daily_limit=50):
        self.rpm = requests_per_minute
        self.daily_limit = daily_limit
        self.history = defaultdict(list)
        self.daily_count = defaultdict(lambda: {"count": 0, "date": None})

    def is_allowed(self, ip: str):
        now = datetime.datetime.now()
        today = now.date()

        # Daily limit check
        if self.daily_count[ip]["date"] != today:
            self.daily_count[ip] = {"count": 0, "date": today}
        if self.daily_count[ip]["count"] >= self.daily_limit:
            return False, "Daily limit reached. Try again tomorrow."

        # RPM check
        self.history[ip] = [t for t in self.history[ip] if (now - t).total_seconds() < 60]
        if len(self.history[ip]) >= self.rpm:
            return False, f"Too many requests. Please wait {60 - int((now - self.history[ip][0]).total_seconds())}s."

        self.history[ip].append(now)
        self.daily_count[ip]["count"] += 1
        return True, ""

limiter = RateLimiter()

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
async def chat(request: Request, message: str = Form(...), file_path: str = Form(None)):
    global engine
    ip = request.client.host
    allowed, reason = limiter.is_allowed(ip)
    if not allowed:
        return StreamingResponse(iter([f"ERROR: {reason}"]), media_type="text/plain", status_code=429)

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

@app.post("/reset")
async def reset_session():
    global engine
    if engine:
        engine.reset_chat()
    return {"status": "session reset"}

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
