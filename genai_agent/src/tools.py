import math
import pandas as pd

def analyze_csv(file_path: str) -> str:
    """Reads a CSV and returns a summary for the LLM to analyze."""
    try:
        df = pd.read_csv(file_path)
        summary = {
            "columns": list(df.columns),
            "rows": len(df),
            "head": df.head(3).to_dict(),
            "description": df.describe().to_dict()
        }
        return f"CSV Summary for {file_path}:\n{summary}"
    except Exception as e:
        return f"Error reading CSV: {str(e)}"

def calculate_metric(expression: str) -> str:
    """Safely evaluates a mathematical expression."""
    try:
        # Note: In production, use a safer math parser or restricted eval
        result = eval(expression, {"__builtins__": None}, {"math": math, "abs": abs, "round": round})
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating metric: {str(e)}"

def lookup_operational_presence(country: str) -> str:
    """Mock database lookup for company operations."""
    ops = {
        "brazil": "Primary hub, 200M+ transactions/month, 3 offices.",
        "mexico": "Secondary hub, specialized in fintech ops.",
        "argentina": "Tech center of excellence, 150+ engineers.",
    }
    return ops.get(country.lower(), "Status unknown for this region.")
