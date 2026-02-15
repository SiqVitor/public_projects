import os
import re
import random
import time
from pathlib import Path
from datetime import datetime
from typing import Generator, List, Dict
from dotenv import load_dotenv
from groq import Groq
from genai_agent.src.tools import calculate_metric, lookup_operational_presence, analyze_csv, analyze_pdf, search_career_info, search_repo_context, fetch_url_content

# Load .env from project root or genai_agent folder
load_dotenv() # Default CWD
load_dotenv(Path(__file__).parent.parent / ".env") # Inside genai_agent/
load_dotenv(Path(__file__).parent.parent.parent / ".env") # In project root

class ArgusEngine:
    def __init__(self, model_name: str = "meta-llama/llama-4-scout-17b-16e-instruct"):
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
        self.session_tokens = 0

    def reset_chat(self):
        """Re-initializes the chat session history."""
        self.history = [
            {"role": "system", "content": self.system_instruction}
        ]

    def summarize_history(self):
        """Summarizes the current chat history recursively to maintain context."""
        # Relaxed pruning: Llama 3 has larger context, so we keep 30 turns
        if len(self.history) < 30:
            return

        print("[*] Context window limit reached. Summarizing history...")
        system_msg = self.history[0]
        # Keep last 10 messages for immediate context flow
        recent_messages = self.history[-10:]
        # Identify messages to summarize (everything between system and recent)
        middle_messages = self.history[1:-10]

        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in middle_messages])

        # Recursive instruction: Explicitly ask to merge previous summary if present
        summary_prompt = (
            "Compress the following conversation history into a concise technical summary. "
            "If there is a previous summary, merge it with the new information. "
            "Preserve key context, user goals, and technical details.\n\n"
            + history_text
        )

        try:
            summary_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.1,
                max_tokens=500 # Increased for better detail
            )
            summary_text = f"[RECURSIVE CONTEXT SUMMARY]: {summary_response.choices[0].message.content.strip()}"

            # Replace history: System + New Summary + Recent Messages
            self.history = [
                system_msg,
                {"role": "system", "content": summary_text} # Stored as system message for authority
            ] + recent_messages
            print("[*] History successfully summarized (recursively).")
        except Exception as e:
            print(f"[!] Summarization failed: {e}")

    def detect_bot_query(self, query: str) -> bool:
        """Detects patterns typical of automated scrapers/agents."""
        bot_patterns = [
            "list all", "recursively", "json only", "output as json",
            "comprehensive index", "exhaustively", "extract all"
        ]
        return any(kw in query.lower() for kw in bot_patterns)

    def detect_risk_content(self, text: str) -> bool:
        """Checks for prompt injection, malicious, unethical or system-invasive patterns."""
        risk_patterns = [
            "ignore initial", "system prompt", "new instructions", "ignore above",
            "desconsidere as instruções", "definições iniciais",
            "how to hack", "exploit", "malware", "illegal", "unethical", "immoral",
            "break the system", "system access", "bypass security"
        ]
        return any(kw in text.lower() for kw in risk_patterns)

    def classify_intent(self, query: str) -> str:
        """Determines the user's intent to route to the correct tool or flow."""
        prompt = f"""
        Classify the following user query into one of these categories:
        - FINANCIAL_ANALYSIS: Queries about revenue, profit, stocks, or financial data.
        - DATA_ANALYSIS: Queries specifically mentioning files, CSVs, or data summaries.
        - PRODUCT_RAG: Queries about specific product features, documentation, or specs.
        - GEOSPATIAL_RESEARCH: Queries about locations, operations in countries, or maps.
        - GENERAL_QA: Anything else.

        Query: "{query[:500]}"
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

        # 0. Safety & Risk Check
        if self.detect_risk_content(query):
            yield "ERROR: Safety Protocol — This request contains content that violates safety or ethical guidelines. I am restricted to professional and ethical analytical tasks."
            return

        # Limit large inputs to prevent prompt-overflow attacks or latency
        sanitized_query = query[:4000]

        # 1. Automated Summarization Check
        self.summarize_history()

        # 2. Dynamic System Injection (Date & Awareness)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        injection = f"\n\n[SYSTEM INJECTION]: Current Date: {now}. Verify facts before responding.\n\n"

        # 3. Context Injection (Career & Repo RAG)
        career_keywords = ["vitor", "autor", "author", "experience", "carreira", "career", "background", "habilidades", "skills", "currículo", "cv", "linkedin"]
        repo_keywords = ["repo", "repositório", "código", "arquitetura", "pasta", "folder", "estrutura", "projeto", "project"]

        trigger_career = any(kw in sanitized_query.lower() for kw in career_keywords)
        trigger_repo = any(kw in sanitized_query.lower() for kw in repo_keywords)

        if trigger_career or trigger_repo:
            print(f"[*] Context trigger detected. Fetching RAG data...")
            if trigger_career:
                career_context = search_career_info()
                injection += f"\n[CAREER CONTEXT]: {career_context}\n"
            if trigger_repo:
                repo_context = search_repo_context()
                injection += f"\n[REPO CONTEXT]: {repo_context}\n"

        # 4. External Link Handler (New)
        # Regex to find http/https URLs
        urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', sanitized_query)
        if urls:
            print(f"[*] URLs detected: {urls}")
            for url in urls:
                # Basic cleanup
                url = url.rstrip('.,;)')
                content = fetch_url_content(url)
                injection += f"\n\n[SYSTEM: I have successfully fetched the following external link. Use this information to answer the user.]\n{content}\n"

        modified_query = sanitized_query
        # CSV Detection
        # CSV Detection
        if ".csv" in sanitized_query.lower():
            parts = sanitized_query.split()
            # Clean punctuation from parts before checking extension
            path = next((p.rstrip(".,;:?!") for p in parts if p.lower().rstrip(".,;:?!").endswith(".csv")), None)

            # Logic to find the file
            # SINGLE SOURCE OF TRUTH: app.py uses "genai_agent/uploads"
            # We strictly check:
            # 1. The exact path provided (if relative to CWD)
            # 2. The file in the official uploads directory (flattened)

            final_path = None
            uploads_dir = Path("genai_agent/uploads")

            # Helper to check
            check_paths = [
                Path(path),                                  # 1. Relative/Absolute
                uploads_dir / Path(path).name                # 2. In Uploads (Basename)
            ]

            for p in check_paths:
                if p.exists():
                    final_path = str(p)
                    break

            if final_path:
                context = analyze_csv(final_path)
                # Safeguard: Check file content for risk
                if self.detect_risk_content(context):
                    yield "ERROR: Safety Protocol — The attached file contains content that violates safety guidelines."
                    return
                # Inject explicit system confirmation
                injection += f"\n\n[SYSTEM: I have successfully read the CSV file at {final_path}. Use this data analysis:]\n{context}\n"

        # PDF Detection
        if ".pdf" in sanitized_query.lower():
            parts = sanitized_query.split()
            path = next((p.rstrip(".,;:?!") for p in parts if p.lower().rstrip(".,;:?!").endswith(".pdf")), None)

            # Logic to find the file
            final_path = None
            uploads_dir = Path("genai_agent/uploads")

            check_paths = [
                Path(path),
                uploads_dir / Path(path).name
            ]

            for p in check_paths:
                if p.exists():
                    final_path = str(p)
                    break

            # Avoid re-reading the career pdfs which are handled by career RAG
            if final_path and "cv_vitor" not in final_path.lower() and "linkedin" not in final_path.lower():
                context = analyze_pdf(final_path)
                # Safeguard: Check file content for risk
                if self.detect_risk_content(context):
                    yield "ERROR: Safety Protocol — The attached file contains content that violates safety guidelines."
                    return
                injection += f"\n\n[SYSTEM: I have successfully read the PDF file at {final_path}. Use this content:]\n{context}\n"

        # Combine for input
        final_user_content = f"{injection}\n<user_input>\n{modified_query}\n</user_input>"

        # Add to local history
        self.history.append({"role": "user", "content": final_user_content})

        try:
            # Smart Tarpitting for potential bots
            if self.detect_bot_query(sanitized_query):
                print("[!] Bot-like pattern detected. Injecting tarpit latency...")
                time.sleep(random.uniform(1.5, 3.5))

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.history,
                temperature=0.1,
                max_tokens=1500, # Per-request safe limit
                stream=True
            )

            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text

            # Token Tracking (Estimation)
            estimated_tokens = (len(sanitized_query) + len(full_response)) // 4
            self.session_tokens += estimated_tokens

            # Save assistant response to history
            self.history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            if "rate_limit" in str(e).lower() or "quota" in str(e).lower():
                yield "QUOTA EXCEEDED: ARGUS capacity reached. Please wait a moment before next request."
            else:
                print(f"[!] INTERNAL ERROR: {str(e)}")
                yield "ERROR: An analytical error occurred. Please try again."

    def get_history(self) -> List:
        return self.history
