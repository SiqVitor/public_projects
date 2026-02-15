import os
import google.generativeai as genai
from typing import Generator, List
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from genai_agent.src.tools import calculate_metric, lookup_operational_presence, analyze_csv, search_career_info, search_repo_context

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
        self.system_instruction = ""
        if prompt_path.exists():
            self.system_instruction = prompt_path.read_text(encoding="utf-8")

        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self.system_instruction
        )
        self.reset_chat()

    def reset_chat(self):
        """Re-initializes the chat session history."""
        self.chat = self.model.start_chat(history=[])

    def summarize_history(self):
        """Summarizes the current chat history to keep context window manageable."""
        if len(self.chat.history) < 16:
            return

        print("[*] Context window limit reached. Summarizing history...")
        # Take the oldest 10 messages to summarize
        history_to_summarize = self.chat.history[:10]
        summary_prompt = "Summarize the following conversation history into a concise but detailed technical brief for context preservation. Focus on key engineering findings and data insights: \n\n"

        history_text = ""
        for msg in history_to_summarize:
            role = "User" if msg.role == "user" else "ARGUS"
            history_text += f"{role}: {msg.parts[0].text}\n"

        summary_response = self.model.generate_content(summary_prompt + history_text)
        summary_text = f"[CONTEXT SUMMARY]: {summary_response.text.strip()}"

        # Keep the latest history and prepend the summary
        remaining_history = self.chat.history[10:]

        # Re-start chat with summarized context as the first message
        new_history = [
            {"role": "user", "parts": ["Previously, we discussed the following context: " + summary_text]},
            {"role": "model", "parts": ["Acknowledged. I have preserved that technical context for our continuing analysis."]}
        ]

        # Map existing remaining history to the required format for start_chat
        for msg in remaining_history:
            new_history.append({"role": msg.role, "parts": [msg.parts[0].text]})

        self.chat = self.model.start_chat(history=new_history)
        print("[*] History successfully summarized and compressed.")

    def detect_prompt_injection(self, text: str) -> bool:
        """Detects common prompt injection patterns to protect system instructions."""
        injection_keywords = [
            "ignore previous instructions",
            "system override",
            "ignore all instructions",
            "new instructions",
            "forget your rules",
            "dan mode",
            "jailbreak",
            "you are now",
            "disregard"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in injection_keywords)

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

        # 0. Prompt Injection Check
        if self.detect_prompt_injection(query):
            yield "ERROR: Safety Protocol — Direct instruction overrides detected. I am fixed to my core analytical protocol."
            return

        # 1. Automated Summarization Check
        self.summarize_history()

        # 2. Dynamic System Injection (Date & Awareness)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        injection = f"\n\n[SYSTEM INJECTION]: Current Date: {now}. Always verify data patterns and engineering facts before responding. Stay anchor to the provided timeframe.\n\n"

        # 3. Context Injection (Career & Repo RAG)
        career_keywords = ["vitor", "autor", "author", "experience", "carreira", "career", "background", "habilidades", "skills", "currículo", "cv", "linkedin"]
        repo_keywords = ["repo", "repositório", "código", "arquitetura", "pasta", "folder", "estrutura", "projeto", "project"]

        trigger_career = any(kw in query.lower() for kw in career_keywords)
        trigger_repo = any(kw in query.lower() for kw in repo_keywords)

        if trigger_career or trigger_repo:
            print(f"[*] Context trigger detected (Career: {trigger_career}, Repo: {trigger_repo}). Fetching context...")

            if trigger_career:
                career_context = search_career_info()
                injection += f"\n[CAREER CONTEXT]: Based on Vitor's professional documents: {career_context}\n"

            # For career questions, repo context provides physical proof of projects
            if trigger_repo or trigger_career:
                repo_context = search_repo_context()
                injection += f"\n[REPO CONTEXT]: Current Repository Structure and Readmes: {repo_context}\n\n"

        modified_query = query
        # Simple file-path detection in query for CSV analysis
        if ".csv" in query.lower():
            # Extract path (heuristic)
            parts = query.split()
            path = next((p for p in parts if p.endswith(".csv")), None)
            if path and os.path.exists(path):
                context = analyze_csv(path)
                modified_query = f"Based on this data: {context}\n"

        # Combine injection with delimited query to prevent spillover
        final_query = f"{injection}\n<user_input>\n{modified_query}\n{query if '.csv' in query.lower() else ''}\n</user_input>"

        response = self.chat.send_message(final_query, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def get_history(self) -> List:
        return self.chat.history
