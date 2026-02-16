"""
Supabase Logger — Fire-and-forget chat logging.
All methods are wrapped in try/except so failures never break the chat.
"""
import os
import hashlib
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv()
load_dotenv(Path(__file__).parent.parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def _post(table: str, data: dict) -> dict | None:
    """POST to Supabase REST API. Returns inserted row or None."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}"
        resp = requests.post(url, json=data, headers=_headers(), timeout=5)
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else None
    except Exception as e:
        print(f"[!] Supabase log failed ({table}): {e}")
        return None


def hash_ip(ip: str) -> str:
    """SHA-256 hash of IP — no PII stored."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def create_conversation(ip: str = "", user_agent: str = "") -> str | None:
    """Create a new conversation row. Returns conversation_id (uuid) or None."""
    row = _post("conversations", {
        "user_ip_hash": hash_ip(ip) if ip else "unknown",
        "user_agent": user_agent[:500] if user_agent else ""
    })
    return row["id"] if row else None


def log_message(
    conversation_id: str,
    role: str,
    content: str,
    response_time_ms: int = None,
    tokens_estimated: int = None
):
    """Log a single message (user or agent)."""
    if not conversation_id:
        return
    data = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content[:10000]  # Cap at 10k chars
    }
    if response_time_ms is not None:
        data["response_time_ms"] = response_time_ms
    if tokens_estimated is not None:
        data["tokens_estimated"] = tokens_estimated
    _post("messages", data)


def log_summarization(
    conversation_id: str,
    summary_text: str,
    message_count: int
):
    """Log a history summarization event."""
    if not conversation_id:
        return
    _post("summarizations", {
        "conversation_id": conversation_id,
        "summary_text": summary_text[:5000],
        "message_count": message_count
    })
