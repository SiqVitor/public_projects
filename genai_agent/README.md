# ARGUS — AI Research & Analysis Agent

A production-grade multi-agent system built with LangGraph that performs automated research, data analysis, and document-grounded Q&A. Designed as an end-to-end demonstration of GenAI engineering practices.

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)]()
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)]()
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

## Features

**Multi-Agent Orchestration** — A LangGraph state machine routes queries to specialized agents (research, analysis, RAG) based on intent classification, with persistent memory and checkpointing.

**RAG Pipeline** — Hybrid retrieval combining dense vector search and sparse BM25 scoring, with source citations on every response.

**Tool Use** — Agents can search the web, execute Python for data analysis, and generate visualizations on the fly.

**Streaming** — Real-time token delivery via Server-Sent Events, with live tool-call status updates.

**Evaluation** — Automated evaluation pipeline measuring faithfulness, relevance, citation accuracy, and latency.

## Architecture

```
User → Streamlit UI → FastAPI → LangGraph Orchestrator
                                    ├── Research Agent (web search + summarization)
                                    ├── Data Analyst Agent (code execution + viz)
                                    └── RAG Agent (vector search + citations)
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Groq (Llama 3) |
| Orchestration | LangGraph |
| RAG | LangChain + ChromaDB |
| Embeddings | Google Gemini |
| API | FastAPI |
| Frontend | Streamlit |
| Database | PostgreSQL |
| Cache | Redis |
| Search | DuckDuckGo |

## Quick Start

```bash
git clone https://github.com/SiqVitor/public_projects.git
cd public_projects/genai_agent

cp .env.example .env
# Fill in your API keys in .env

poetry install --with dev
docker-compose up -d

# API
poetry run uvicorn argus.api.app:app --reload

# Frontend (separate terminal)
poetry run streamlit run src/frontend/app.py
```

## Interaction & Evaluation

Since the core LangGraph engine is a proprietary case study, you can explore the system's logic using the provided simulation tools:

### 1. Interactive CLI Demo
Experience the grounding and citation behavior in an interactive session.
```bash
python genai_agent/demo/interactive_demo.py
```
**Try asking:**
- "What was the Q3 revenue?"
- "Who is the CEO?" (to see how it handles missing evidence)

### 2. Automated Evaluation Pipeline
Run the metrics-first evaluation to check faithfulness and citation accuracy.
```bash
bash genai_agent/demo/run_local_eval.sh
```
Results will be saved to `genai_agent/demo/results/eval_report.json`.

## License

Proprietary — see [LICENSE](LICENSE)

---

Built by **Vitor de Siqueira Rodrigues**
