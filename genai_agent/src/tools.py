import math
import os
import requests
import json
import pandas as pd
from bs4 import BeautifulSoup
from pypdf import PdfReader

def fetch_url_content(url: str) -> str:
    """Fetches text content from a public URL. Gracefully handles walls."""
    try:
        # 1. Check for walled gardens (LinkedIn, etc)
        blocked_domains = ["linkedin.com", "facebook.com", "instagram.com"]
        if any(domain in url.lower() for domain in blocked_domains):
             return f"⚠️ Access Restricted: The URL {url} requires authentication or is a walled platform. Please export the page to PDF or copy-paste the text here."

        # 2. Fetch content with browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # 3. Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 3.1 Next.js / SPA Handling
        # Many modern sites (iFood, Vercel apps) store data in a JSON script tag
        next_data = soup.find("script", {"id": "__NEXT_DATA__"})
        extra_content = ""
        if next_data:
            try:
                data = json.loads(next_data.string)
                # Recursively find long strings in the JSON (likely content)
                def extract_strings(obj, min_len=100):
                    text_parts = []
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            text_parts.extend(extract_strings(v, min_len))
                    elif isinstance(obj, list):
                        for item in obj:
                            text_parts.extend(extract_strings(item, min_len))
                    elif isinstance(obj, str) and len(obj) > min_len:
                        # Clean html tags if present
                        clean_text = BeautifulSoup(obj, 'html.parser').get_text(separator=' ', strip=True)
                        text_parts.append(clean_text)
                    return text_parts

                found_texts = extract_strings(data.get("props", {}).get("pageProps", {}))
                if found_texts:
                    extra_content = "\n\n[HIDDEN CONTENT EXTRACTED FROM APP DATA]:\n" + "\n".join(found_texts[:5]) # Limit to top 5 chunks
            except:
                pass

        # Remove scripts, styles, nav, footer
        for script in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript", "svg"]):
            script.decompose()

        text = soup.get_text(separator=' ', strip=True)

        # Clean up whitespace
        text = " ".join(text.split())

        # Append extra content found in JSON
        text += extra_content

        # 4. Success Validation
        # If text is too short, it might be a JS-only site (SPA) that failed to scrape
        if len(text) < 200 and not extra_content:
             return (f"⚠️ SPA Detected: The URL {url} appears to be a Single Page Application that loads content via JavaScript. "
                     f"I cannot scrape it directly. Please copy and paste the relevant text (e.g., job description) here so I can analyze it.")

        # Limit content size
        if len(text) > 12000:
             text = text[:12000] + "... [Content Truncated]"

        title = soup.title.string if soup.title else "No Title"
        return f"--- EXTERNAL CONTENT: {url} (Title: {title}) ---\n{text}\n--- END OF CONTENT ---"

    except Exception as e:
        return f"⚠️ Error fetching URL: {str(e)} (Note: This site blocks automated access. Please copy/paste the text.)"

def analyze_csv(file_path: str) -> str:
    """Reads a CSV and returns a sampled summary for the LLM to analyze."""
    try:
        df = pd.read_csv(file_path)
        cols = list(df.columns)
        row_count = len(df)

        # Sampling logic for efficiency
        if row_count > 1000:
            sample_head = df.head(10).to_dict(orient='records')
            sample_tail = df.tail(10).to_dict(orient='records')
            stats = df.describe().to_dict()
            msg = f"(Sampled! Total rows: {row_count}. Showing first/last 10 rows for context.)"
        else:
            sample_head = df.to_dict(orient='records')
            sample_tail = []
            stats = df.describe().to_dict()
            msg = f"(Full dataset loaded. Total rows: {row_count}.)"

        return (f"--- DATA ANALYSIS REPORT: {file_path} ---\n"
                f"{msg}\n\n"
                f"### 1. Structure\n- Columns: {cols}\n- Rows: {row_count}\n\n"
                f"### 2. Statistics (Numerical)\n{json.dumps(stats, indent=2)}\n\n"
                f"### 3. Data Sample (Head)\n{json.dumps(sample_head, indent=2)}\n\n"
                f"### 4. Data Sample (Tail)\n{json.dumps(sample_tail, indent=2)}\n"
                f"--- END OF REPORT ---")
    except Exception as e:
        return f"Error reading CSV: {str(e)}"

def analyze_pdf(file_path: str) -> str:
    """Extracts text from a PDF efficiently (first/last pages + middle chunks)."""
    try:
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)

        extracted_text = ""
        # Strategy: Read first, middle, and last page to save tokens
        pages_to_read = sorted(list(set([0, total_pages // 2, total_pages - 1])))

        for p_idx in pages_to_read:
            if p_idx < total_pages:
                extracted_text += f"\n--- Page {p_idx + 1} ---\n"
                extracted_text += reader.pages[p_idx].extract_text()[:2000] # Limit per page

        return f"--- PDF REPORT: {file_path} ---\nTotal Pages: {total_pages}\nExtracted Content (Sampled):\n{extracted_text}\n--- END OF REPORT ---"
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def search_career_info() -> str:
    """Reads Vitor's CV and LinkedIn PDFs to provide career context for RAG."""
    career_files = [
        "cv_vitor_rodrigues.pdf",
        "Vitor Rodrigues _ LinkedIn.pdf"
    ]

    # Search relative to this file's location (robust for Docker/HF Spaces)
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    search_paths = [
        os.path.join(tools_dir, ".."),           # genai_agent/
        os.path.join(tools_dir, "..", ".."),      # project root
        ".",                                       # CWD fallback
    ]
    all_context = ""

    for file_name in career_files:
        found_path = None
        for base in search_paths:
            test_path = os.path.join(base, file_name)
            if os.path.exists(test_path):
                found_path = test_path
                break

        if found_path:
            try:
                reader = PdfReader(found_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                all_context += f"--- Source: {file_name} ---\n{text}\n\n"
            except Exception as e:
                all_context += f"--- Error reading {file_name}: {str(e)} ---\n"

    return all_context if all_context else "No career documents found."

def calculate_metric(expression: str) -> str:
    """Safely evaluates a mathematical expression."""
    try:
        # Note: In production, use a safer math parser or restricted eval
        result = eval(expression, {"__builtins__": None}, {"math": math, "abs": abs, "round": round})
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating metric: {str(e)}"

def generate_code_map(root_dir: str) -> str:
    """Scans Python files to generate an AST-based architectural summary."""
    summary = []

    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") and "test" not in file:
                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, root_dir)

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())

                    file_summary = [f"\n📄 File: {rel_path}"]

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            file_summary.append(f"  class {node.name}")
                            for sub in node.body:
                                if isinstance(sub, ast.FunctionDef):
                                    doc = ast.get_docstring(sub) or ""
                                    doc_line = doc.split('\n')[0] if doc else ""
                                    file_summary.append(f"    def {sub.name}: {doc_line}")
                        elif isinstance(node, ast.FunctionDef) and isinstance(node.parent, ast.Module):
                             # Top level functions (hacky check, simplistic)
                             pass

                    # Simplistic AST walk doesn't track parent easily,
                    # so let's stick to a cleaner iteration for top-level

                    file_structure = []
                    for node in tree.body:
                        if isinstance(node, ast.ClassDef):
                            methods = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    doc = ast.get_docstring(item)
                                    desc = f" ({doc.split('.')[0]})" if doc else ""
                                    methods.append(f"{item.name}{desc}")
                            file_structure.append(f"  📦 Class {node.name}: {', '.join(methods)}")
                        elif isinstance(node, ast.FunctionDef):
                             doc = ast.get_docstring(node)
                             desc = f" ({doc.split('.')[0]})" if doc else ""
                             file_structure.append(f"  ⚡ Func {node.name}{desc}")

                    if file_structure:
                        summary.extend(file_summary[:1] + file_structure)

                except Exception as e:
                    summary.append(f"  ⚠️ Error parsing {rel_path}: {e}")

    return "\n".join(summary)

def search_repo_context() -> str:
    """Generates a map of the repository structure and architectural summary."""
    ignore_dirs = [".git", "__pycache__", "node_modules", ".venv", "venv", ".gemini", "brain"]
    base_path = "."
    tree = []
    readme_summaries = ""

    # 1. Generate File Tree
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        level = root.replace(base_path, '').count(os.sep)
        indent = ' ' * 4 * level
        tree.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            if not f.startswith('.'):
                 tree.append(f"{sub_indent}{f}")
            if f.lower() == "readme.md":
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as rf:
                         readme_summaries += f"\n--- README in {root} ---\n{rf.read(2000)}...\n"
                except: pass

    # 2. Generate Code Architecture (AST)
    code_map = generate_code_map(".")

    repo_map = "\n".join(tree)
    github_context = "Public Repository URL: https://github.com/SiqVitor/public_projects (Contains full source code for 'genai_agent' and other portfolio items)."

    return f"=== REPOSITORY STRUCTURE ===\n{repo_map}\n\n=== CODE ARCHITECTURE (Key Classes & Functions) ===\n{code_map}\n\n=== README SUMMARIES ===\n{readme_summaries}\n\n{github_context}"

def lookup_operational_presence(country: str) -> str:
    """Mock database lookup for company operations."""
    ops = {
        "brazil": "Primary hub, 200M+ transactions/month, 3 offices.",
        "mexico": "Secondary hub, specialized in fintech ops.",
        "argentina": "Tech center of excellence, 150+ engineers.",
    }
    return ops.get(country.lower(), "Status unknown for this region.")
