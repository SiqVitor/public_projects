import os
import google.generativeai as genai
from typing import Generator, List
from pathlib import Path
from dotenv import load_dotenv
from genai_agent.src.tools import calculate_metric, lookup_operational_presence, analyze_csv

# Load .env from project root or genai_agent folder
load_dotenv() # Default CWD
load_dotenv(Path(__file__).parent.parent / ".env") # Inside genai_agent/
load_dotenv(Path(__file__).parent.parent.parent / ".env") # In project root

class ArgusEngine:
    def __init__(self, model_name: str = "models/gemini-flash-latest"):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key.strip() == "":
            raise ValueError("GOOGLE_API_KEY is empty or missing. Please fill it in 'genai_agent/.env' and rebuild.")

        genai.configure(api_key=api_key)

        # Load structured prompt
        prompt_path = Path(__file__).parent / "prompts" / "system_prompt.md"
        system_instruction = ""
        if prompt_path.exists():
            system_instruction = prompt_path.read_text(encoding="utf-8")

        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction
        )
        self.chat = self.model.start_chat(history=[])

    def classify_intent(self, query: str) -> str:
        """Determines the user's intent to route to the correct tool or flow."""
        prompt = f"""
        Classify the following user query into one of these categories:
        - FINANCIAL_ANALYSIS: Queries about revenue, profit, stocks, or financial data.
        - DATA_ANALYSIS: Queries specifically mentioning files, CSVs, or data summaries.
        - PRODUCT_RAG: Queries about specific product features, documentation, or specs.
        - GEOSPATIAL_RESEARCH: Queries about locations, operations in countries, or maps.
        - GENERAL_QA: Anything else.

        Query: "{query}"
        Category:"""

        response = self.model.generate_content(prompt)
        return response.text.strip().upper()

    def stream_query(self, query: str) -> Generator[str, None, None]:
        """Streams the LLM response, incorporating tool outputs if needed."""
        context = ""

        # Simple file-path detection in query for CSV analysis
        if ".csv" in query.lower():
            # Extract path (heuristic)
            parts = query.split()
            path = next((p for p in parts if p.endswith(".csv")), None)
            if path and os.path.exists(path):
                context = analyze_csv(path)
                query = f"Based on this data: {context}\nUser Question: {query}"

        response = self.chat.send_message(query, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def get_history(self) -> List:
        return self.chat.history
