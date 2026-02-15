"""Interactive demo for ARGUS — GenAI Research & Analysis Agent.

# Now powered by a real LLM engine (Groq / Llama 3.3).
Ensure GOOGLE_API_KEY is set in your .env file.
"""

import os
import sys

from genai_agent.src.engine import ArgusEngine

def print_agent_box(text_generator):
    print("\n" + "="*50)
    print("ARGUS Agent Response:")
    print("-" * 50)

    # Check if input is a generator (streaming) or string
    if hasattr(text_generator, "__iter__") and not isinstance(text_generator, str):
        for chunk in text_generator:
            sys.stdout.write(chunk)
            sys.stdout.flush()
    else:
        sys.stdout.write(text_generator)

    print("\n" + "="*50 + "\n")

def main():
    print("\n=== ARGUS — AI Research & Analysis Agent (LIVE ENGINE) ===")
    print("Tip: Mention a CSV path in your query to analyze data.")
    print("Example: 'Summarize genai_agent/demo/test_expenses.csv'\n")

    try:
        engine = ArgusEngine()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please check genai_agent/.env and provide a valid API key.")
        return
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    print("Agent is ready. Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            query = input("User Question: ").strip()
        except EOFError:
            break

        if not query:
            continue

        if query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # 1. Intent Classification (internal check)
        intent = engine.classify_intent(query)
        print(f"[*] Analyzing query... (Detected Intent: {intent})")

        # 2. Real Streaming Response
        print("[*] Generating response...")
        response_gen = engine.stream_query(query)
        print_agent_box(response_gen)

if __name__ == "__main__":
    # Ensure we are in the right directory or path is added
    sys.path.append(os.getcwd())
    main()
