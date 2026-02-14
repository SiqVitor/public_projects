import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Load API Key
load_dotenv()
load_dotenv(Path("genai_agent/.env"))

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
else:
    genai.configure(api_key=api_key)
    print("Available Models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name} ({m.display_name})")
    except Exception as e:
        print(f"Error listing models: {e}")
