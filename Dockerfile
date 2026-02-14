FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project code and toolkit
COPY ds_tools/ ds_tools/
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e ds_tools/

# Copy only necessary folders for the Agent
COPY genai_agent/ genai_agent/
COPY ds_tools/ ds_tools/
COPY .env .
COPY README.md .
COPY requirements.txt .

# Expose port for Hugging Face Spaces / Production
EXPOSE 7860

# CMD for uvicorn launch
CMD ["python", "-m", "uvicorn", "genai_agent.src.app:app", "--host", "0.0.0.0", "--port", "7860"]
