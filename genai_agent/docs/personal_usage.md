# ARGUS Usage Guide: Personal & Professional Scenarios

ARGUS is designed to be a versatile Research & Analysis agent. Below are instructions on how to set it up and use it for your own personal use cases.

## 🚀 1. Setup
1.  **API Key**: Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2.  **Environment**:
    - Copy `genai_agent/.env.example` to `genai_agent/.env`.
    - Paste your key: `GOOGLE_API_KEY=your_actual_key_here`.
3.  **Install Dependencies**:
    ```bash
    pip install -r genai_agent/requirements.txt
    ```

## 💡 2. Personal Use Case Scenarios

### Scenario A: Personal Financial Assistant
You can use ARGUS to analyze your personal spending or investment data.
- **Workflow**:
  1. Provide a CSV of your expenses.
  2. Ask: *"Analyze my spending in the 'Grocery' category over the last 3 months. What is the trend?"*
- **Grounding**: ARGUS uses the `calculate_metric` tool to ensure math accuracy, unlike standard chatbots that might hallucinate numbers.

### Scenario B: Technical Research & Deep Dives
Use ARGUS to stay updated on niche technologies or research papers.
- **Workflow**:
  1. Ask: *"Research the latest advancements in Llama-3 quantization techniques."*
- **Grounding**: ARGUS classifies this as `GENERAL_QA` but can be extended with a RAG tool to browse specific local documentation.

### Scenario C: Regional Operational Planning
If you are planning a business expansion or a trip.
- **Workflow**:
  1. Ask: *"What is the operational landscape for fintech in Mexico?"*
- **Grounding**: ARGUS uses the `lookup_operational_presence` tool to pull verified data about company hubs.

## 🛠️ 3. Extending the Agent
To add your own data or tools:
1.  **New Tools**: Add functions to `genai_agent/src/tools.py`.
2.  **Intent Mapping**: Update `classify_intent` in `genai_agent/src/engine.py` to recognize your new use case.
3.  **Knowledge Base**: Insert file-reading logic in `stream_query` to provide local context (RAG).

## 🖥️ 4. Running the Agent
```bash
python genai_agent/demo/interactive_demo.py
```
> [!TIP]
> Use the streaming output to watch the agent's "thought process" as it classifies your intent before responding.
