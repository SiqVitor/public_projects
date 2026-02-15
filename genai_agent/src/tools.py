import math
import os
import pandas as pd
from pypdf import PdfReader

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
            sample_head = df.head(5).to_dict(orient='records')
            sample_tail = None
            stats = df.describe().to_dict()
            msg = f"(Full scan. Total rows: {row_count}.)"

        summary = {
            "available_columns": cols,
            "row_count": row_count,
            "sample_head": sample_head,
            "sample_tail": sample_tail,
            "numerical_statistics": stats,
            "efficiency_note": msg
        }
        return f"--- DATA REPORT: {file_path} ---\n{msg}\nColumns: {cols}\nSummary: {summary}\n--- END OF REPORT ---"
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

    # Check current directory and root
    search_paths = [".", ".."]
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

def search_repo_context() -> str:
    """Generates a map of the repository structure and summary of project READMEs."""
    ignore_dirs = [".git", "__pycache__", "node_modules", ".venv", "venv", ".gemini", "brain"]
    base_path = "."
    tree = []
    readme_summaries = ""

    # Check for folders in root
    for root, dirs, files in os.walk(base_path):
        # Filter hidden/ignore dirs
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]

        level = root.replace(base_path, '').count(os.sep)
        indent = ' ' * 4 * level
        tree.append(f"{indent}{os.path.basename(root)}/")

        sub_indent = ' ' * 4 * (level + 1)
        for f in files:
            if not f.startswith('.'):
                tree.append(f"{sub_indent}{f}")

            # Index README content
            if f.lower() == "readme.md":
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as rf:
                        content = rf.read(500) # Get first 500 chars as summary
                        readme_summaries += f"\n--- README in {root} ---\n{content}...\n"
                except:
                    pass

    repo_map = "\n".join(tree)
    return f"Project Structure:\n{repo_map}\n\nProject README Summaries:\n{readme_summaries}"

def lookup_operational_presence(country: str) -> str:
    """Mock database lookup for company operations."""
    ops = {
        "brazil": "Primary hub, 200M+ transactions/month, 3 offices.",
        "mexico": "Secondary hub, specialized in fintech ops.",
        "argentina": "Tech center of excellence, 150+ engineers.",
    }
    return ops.get(country.lower(), "Status unknown for this region.")
