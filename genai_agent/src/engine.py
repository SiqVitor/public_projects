import os
import json
from pathlib import Path
from datetime import datetime
from typing import Generator, List, Dict
from dotenv import load_dotenv
from groq import Groq
from genai_agent.src.tools import calculate_metric, lookup_operational_presence, analyze_csv, search_career_info, search_repo_context

# Load .env from project root or genai_agent folder
load_dotenv() # Default CWD
load_dotenv(Path(__file__).parent.parent / ".env") # Inside genai_agent/
load_dotenv(Path(__file__).parent.parent.parent / ".env") # In project root

class ArgusEngine:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key.strip() == "":
            raise ValueError("GROQ_API_KEY is empty or missing. Please fill it in 'genai_agent/.env' and rebuild.")

        self.model_name = model_name
        self.client = Groq(api_key=api_key)

        # Load structured prompt
        prompt_path = Path(__file__).parent / "prompts" / "system_prompt.md"
        self.system_instruction = ""
        if prompt_path.exists():
            self.system_instruction = prompt_path.read_text(encoding="utf-8")

        self.reset_chat()

    def reset_chat(self):
        """Re-initializes the chat session history."""
        self.history = [
            {"role": "system", "content": self.system_instruction}
        ]

    def summarize_history(self):
        """Summarizes the current chat history to keep context window manageable."""
        # Groq/Llama usually have large context windows, but we'll prune if it exceeds 20 messages
        if len(self.history) < 20:
            return

        print("[*] Context window limit reached. Summarizing history...")
        # Keep system prompt and latest 5 messages
        system_msg = self.history[0]
        recent_messages = self.history[-5:]
        middle_messages = self.history[1:-5]

        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in middle_messages])
        summary_prompt = "Summarize this technical conversation concisely for context preservation: \n\n" + history_text

        try:
            summary_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1
            )
            summary_text = f"[CONTEXT SUMMARY]: {summary_response.choices[0].message.content.strip()}"

            self.history = [
                system_msg,
                {"role": "assistant", "content": "Acknowledged. I have preserved the previous context: " + summary_text}
            ] + recent_messages
            print("[*] History successfully summarized.")
        except Exception as e:
            print(f"[!] Summarization failed: {e}")

    def detect_prompt_injection(self, query: str) -> bool:
        """Heuristic check for system instruction override attempts."""
        attack_keywords = ["ignore initial", "system prompt", "new instructions", "ignore above", "desconsidere as instruções"]
        return any(kw in query.lower() for kw in attack_keywords)

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

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50
        )
        return response.choices[0].message.content.strip().upper()

    def stream_query(self, query: str) -> Generator[str, None, None]:
        """Streams the LLM response via Groq."""

        # 0. Prompt Injection Check
        if self.detect_prompt_injection(query):
            yield "ERROR: Safety Protocol — Direct instruction overrides detected. I am fixed to my core analytical protocol."
            return

        # 1. Automated Summarization Check
        self.summarize_history()

        # 2. Dynamic System Injection (Date & Awareness)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        injection = f"\n\n[SYSTEM INJECTION]: Current Date: {now}. Always verify data patterns and engineering facts before responding.\n\n"

        # 3. Context Injection (Career & Repo RAG)
        career_keywords = ["vitor", "autor", "author", "experience", "carreira", "career", "background", "habilidades", "skills", "currículo", "cv", "linkedin"]
        repo_keywords = ["repo", "repositório", "código", "arquitetura", "pasta", "folder", "estrutura", "projeto", "project"]

        trigger_career = any(kw in query.lower() for kw in career_keywords)
        trigger_repo = any(kw in query.lower() for kw in repo_keywords)

        if trigger_career or trigger_repo:
            print(f"[*] Context trigger detected. Fetching RAG data...")
            if trigger_career:
                career_context = search_career_info()
                injection += f"\n[CAREER CONTEXT]: {career_context}\n"
            if trigger_repo or trigger_career:
                repo_context = search_repo_context()
                injection += f"\n[REPO CONTEXT]: {repo_context}\n"

        modified_query = query
        # CSV Detection
        if ".csv" in query.lower():
            parts = query.split()
            path = next((p for p in parts if p.endswith(".csv")), None)
            if path and os.path.exists(path):
                context = analyze_csv(path)
                modified_query = f"Based on this data: {context}\nUser Question: {query}"

        # Combine for Llama's input
        final_user_content = f"{injection}\n<user_input>\n{modified_query}\n</user_input>"

        # Add to local history
        self.history.append({"role": "user", "content": final_user_content})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                temperature=0.1, # Groundedness
                stream=True
            )

            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text

            # Save assistant response to history
            self.history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            if "rate_limit" in str(e).lower():
                yield "QUOTA EXCEEDED: Groq rate limit reached. Please wait a moment."
            else:
                print(f"[!] INTERNAL ERROR: {str(e)}")
                yield "ERROR: An analytical error occurred. Please try again."

    def get_history(self) -> List:
        return self.history
