# ARGUS — AI Research & Analysis Agent

> Production-ready multi-agent system built with LangGraph, demonstrating end-to-end GenAI engineering.

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)]()
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)]()
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

## Features

- **Multi-Agent Orchestration** — LangGraph state machine with intelligent routing
- **RAG Pipeline** — Hybrid search (dense + sparse) with citations
- **Tool Use** — Web search, data analysis, visualization generation
- **Streaming** — Real-time token streaming via SSE
- **Evaluation** — Automated evaluation pipeline with custom metrics
- **Production-Ready** — Docker, CI/CD, rate limiting, structured logging

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
# Clone
git clone https://github.com/YOUR_USERNAME/argus.git
cd argus

# Setup environment
cp .env.example .env
# Fill in your API keys in .env

# Install dependencies
poetry install --with dev

# Start infrastructure
docker-compose up -d

# Run the API
poetry run uvicorn argus.api.app:app --reload

# Run the frontend (separate terminal)
poetry run streamlit run src/frontend/app.py
```

## Evaluation Results

_Coming soon_

## License

Proprietary — see [LICENSE](LICENSE)

---

Built by **Vitor de Siqueira Rodrigues** — Senior ML Engineer
