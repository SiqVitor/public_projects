FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install ds_tools first (local dependency)
COPY ds_tools/ ds_tools/
RUN pip install --no-cache-dir -e ds_tools/

# Install dependencies for all systems
RUN pip install --no-cache-dir \
    lightgbm>=4.0 \
    matplotlib>=3.7 \
    pandas \
    scikit-learn \
    google-generativeai \
    python-dotenv \
    joblib \
    fastapi \
    uvicorn \
    python-multipart

# Copy all demo code and config
COPY . .

# Expose port for Hugging Face Spaces
EXPOSE 7860

# Run the Unified Portfolio UI on HF port
CMD ["python", "-m", "uvicorn", "genai_agent.src.app:app", "--host", "0.0.0.0", "--port", "7860"]
