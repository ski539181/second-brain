#!/usr/bin/env python3
"""
llm_helper.py - Shared TokenRouter LLM call

Single function to call TokenRouter. Uses reasoning_effort=low by default.
Cost: ~$0.0001/call (M3 cheap).

Usage:
    from llm_helper import llm_call
    result = llm_call("Your prompt", max_tokens=300)
"""
import json
import subprocess
from pathlib import Path

HERMES = Path.home() / ".hermes"
KEY_FILE = HERMES / "config" / "tokenrouter.key"
API_URL = "https://api.tokenrouter.com/v1/chat/completions"
MODEL = "MiniMax-M3"


def llm_call(prompt, max_tokens=300, effort="low", timeout=30):
    """
    Call TokenRouter M3. Returns text or None on error.
    cost: ~$0.0001/call at low effort.
    """
    if not KEY_FILE.exists():
        return None
    api_key = KEY_FILE.read_text().strip()
    try:
        result = subprocess.run([
            "curl", "-s", "-X", "POST", API_URL,
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "reasoning_effort": effort,
            }),
        ], capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return f"Error: {e}"
    return None


if __name__ == "__main__":
    # Test
    r = llm_call("Say 'OK' in 5 words", max_tokens=20)
    print(f"Test: {r}")
