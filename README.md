# Vitor Rodrigues — ML Engineering Portfolio

**Senior Machine Learning Engineer** — fraud prevention, GenAI agents, production ML systems.

## TL;DR

- **Fraud prevention at scale**: Designed and deployed end-to-end ML pipelines (LightGBM, PyTorch with entity embeddings) processing 200M+ rows/month at Mercado Livre. Savings of $30k–$50k USD/month in prevented chargebacks and account takeovers.
- **GenAI agent automation**: Built an autonomous agent framework (LangChain/LangGraph) to automate ATO report review, reducing manual workload by 70% and freeing 15–20 analysts.
- **Production ML ownership**: Full lifecycle — BigQuery/Databricks ingestion, MLflow experiment tracking and model registry, Docker containerised deployment (GCP Vertex AI), Prometheus/Grafana monitoring, canary rollout with automated rollback.

## Tech Stack

| Area | Tools |
|------|-------|
| ML / DL | scikit-learn, LightGBM, XGBoost, CatBoost, PyTorch (DDP, AMP, TorchScript, ONNX) |
| GenAI | LangChain, LangGraph, RAG (ChromaDB), Groq/Llama 3 |
| Data | Python, SQL, BigQuery, Azure Databricks, pandas, NumPy |
| MLOps | MLflow (tracking + registry), Docker, GCP Vertex AI, CI/CD |
| Monitoring | Prometheus, Grafana, Evidently AI, PSI/KS drift detection |
| Serving | FastAPI, containerised endpoints, canary rollout |

## Case Studies

| Project | Summary | Demo |
|---------|---------|------|
| [Fraud Detection](fraud_detection/) | End-to-end fraud pipeline: IEEE-CIS + synthetic data, LightGBM, PyTorch, calibration, monitoring | `bash fraud_detection/demo/run_demo.sh` |
| [ARGUS — GenAI Agent](genai_agent/) | Multi-agent RAG system with citation evaluation (WIP) | `bash genai_agent/demo/run_local_eval.sh` |
| [Real-Time ML System](realtime_ml_system/) | Online inference pipeline: streaming features, latency tracking, batch/online separation | `bash realtime_ml_system/demo/run_demo.sh` |
| [ML Platform](ml_platform/) | ML lifecycle orchestration: validation → training → evaluation → model registry | `bash ml_platform/demo/run_pipeline.sh` |

### Supporting Projects

| Project | Description |
|---------|-------------|
| [ds_tools](ds_tools/) | Reusable ML toolkit — sklearn transformers, evaluation reports, drift monitoring |
| [Kaggle Competitions](kaggle/) | House Prices (top 12.5%), Titanic, applied statistics |

## 🛡️ ARGUS — Analytical Research Portal

Experience the transition from "demo mocks" to **real production logic** through a unified data analysis portal.

### 🚀 Quick Start (Docker)
1.  **Build**: `docker build -t argus-agent .`
2.  **Run**: `docker run -p 7860:7860 argus-agent`
3.  **Explore**: Open [http://localhost:7860](http://localhost:7860) in your browser.

### 🕹️ What to Test in the Workspace:
1.  **ARGUS Chat**: Ask *"Analyze the trends in genai_agent/demo/test_expenses.csv"*. (Note: Requires Groq API Key in `.env`).
2.  **CSV Tooling**: Upload a personal CSV using the paperclip icon and ask ARGUS to summarize it.
3.  **Pro Analysis**: Request complex interpretations of portfolio files or data patterns.
4.  **Security Layer**: Experience integrated rate limiting and privacy disclosures.

---

## 🚀 Alternative Manual Run

Requires Python 3.10+.
```bash
# Install local toolkit and dependencies
pip install -e ds_tools/
pip install -r genai_agent/requirements.txt
pip install lightgbm pandas scikit-learn

# Run all demos
bash fraud_detection/demo/run_demo.sh
python realtime_ml_system/demo/online_inference.py
python ml_platform/demo/pipeline.py
```

---

## 📚 Documentation

| Document | Audience |
|----------|----------|
| [Architecture](architecture.md) | Technical interviewers — cross-project design patterns |

---

Built by **Vitor de Siqueira Rodrigues** · [LinkedIn](https://linkedin.com/in/r-vitor) · [GitHub](https://github.com/SiqVitor)
