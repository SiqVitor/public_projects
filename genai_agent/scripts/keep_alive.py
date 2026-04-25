#!/usr/bin/env python3
"""
Keep-alive script for Hugging Face Space.

Behavior:
- Picks a random message from a small list and appends " [keep]".
- Always attempts to send that message to SPACE_URL + "/chat" via a simple form-encoded POST.
- If POST fails or returns non-2xx, falls back to GET on the root path to wake the frontend.
- Exits with code 0 on success, non-zero on failure.

Usage:
    python3 scripts/keep_alive.py

Environment:
    SPACE_URL - base URL of your space (default: https://siqvitor-argus.hf.space)
"""

from __future__ import annotations

import random
import sys
import urllib.parse
import urllib.request
from typing import Tuple

SPACE_URL = "https://siqvitor-argus.hf.space"
import os

SPACE_URL = os.getenv("SPACE_URL", SPACE_URL)


MESSAGES = [
    "Olá",
    "Como vai",
    "Me conte uma piada",
    "Qual é a previsão do tempo hoje",
    "Qual é a capital da França",
    "Me ajude a escrever um email formal",
    "Qual é o melhor livro de ficção científica",
]


def post_chat(space_url: str, message: str, timeout: int = 25) -> Tuple[bool, str]:
    """POST form-encoded 'message' to /chat. Returns (ok, info)."""
    url = space_url.rstrip("/") + "/chat"
    data = urllib.parse.urlencode({"message": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "keep-alive-script/1.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", resp.getcode())
            return 200 <= int(code) < 300, f"POST {url} -> {code}"
    except Exception as e:
        return False, f"POST {url} failed: {e}"


def get_root(space_url: str, timeout: int = 15) -> Tuple[bool, str]:
    """GET root path /. Returns (ok, info)."""
    url = space_url.rstrip("/") + "/"
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "keep-alive-script/1.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", resp.getcode())
            return 200 <= int(code) < 300, f"GET {url} -> {code}"
    except Exception as e:
        return False, f"GET {url} failed: {e}"


def main() -> int:
    msg = random.choice(MESSAGES) + " [keep]"
    print(f"Keep-alive: sending message: {msg!r} to {SPACE_URL}")

    ok, info = post_chat(SPACE_URL, msg)
    print(info)
    if ok:
        print("Keep-alive: POST succeeded.")
        return 0

    print("Keep-alive: POST failed or non-2xx; falling back to GET /")
    ok2, info2 = get_root(SPACE_URL)
    print(info2)
    if ok2:
        print("Keep-alive: GET / succeeded.")
        return 0

    print("Keep-alive: both POST and GET failed.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
