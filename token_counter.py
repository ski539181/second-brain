#!/usr/bin/env python3
"""
token_counter.py - Accurate token counter using tiktoken

Tracks:
- Per-call input/output tokens (logged to ~/.hermes/logs/tokens.jsonl)
- Daily totals
- By-direction (input vs output)
- Estimated cost (deepseek-v4-flash rate)

Token cost: 0 (local Python, no LLM)

Usage:
    # Count a string
    python3 token_counter.py count "<text>"

    # Log a call
    python3 token_counter.py log <direction> <text>

    # Show stats
    python3 token_counter.py stats
"""
import json
import time
from datetime import datetime
from pathlib import Path

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False

HERMES = Path.home() / ".hermes"
LOG_DIR = HERMES / "logs"
LOG_FILE = LOG_DIR / "tokens.jsonl"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Approximate costs (deepseek-v4-flash via TokenRouter)
COST_PER_1M_INPUT = 0.14   # $ per 1M tokens (input)
COST_PER_1M_OUTPUT = 0.28  # $ per 1M tokens (output)


def count_tokens(text: str) -> int:
    """Count tokens accurately via tiktoken, fallback to char/4 estimate."""
    if _HAS_TIKTOKEN:
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            pass
    # Fallback: ~1 token per 4 chars (English), less accurate for Thai
    # Thai: ~1 token per 2 chars
    thai_chars = sum(1 for c in text if '\u0e00' <= c <= '\u0e7f')
    other_chars = len(text) - thai_chars
    return (thai_chars // 2) + (other_chars // 4) + 1


def log_call(direction: str, text: str, model: str = "MiniMax-M3"):
    """Log a single LLM call (input or output)."""
    entry = {
        "ts": time.time(),
        "iso": datetime.now().isoformat(),
        "direction": direction,
        "tokens": count_tokens(text),
        "model": model,
        "chars": len(text),
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["tokens"]


def daily_stats():
    """Aggregate today's tokens and cost."""
    if not LOG_FILE.exists():
        return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0}

    today = datetime.now().strftime("%Y-%m-%d")
    in_tok = out_tok = 0
    for line in LOG_FILE.read_text().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if not entry.get("iso", "").startswith(today):
                continue
            if entry.get("direction") == "input":
                in_tok += entry["tokens"]
            elif entry.get("direction") == "output":
                out_tok += entry["tokens"]
        except Exception:
            continue
    cost = (in_tok / 1_000_000) * COST_PER_1M_INPUT + (out_tok / 1_000_000) * COST_PER_1M_OUTPUT
    return {
        "date": today,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "cost_usd": round(cost, 4),
        "method": "tiktoken" if _HAS_TIKTOKEN else "estimate",
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: token_counter.py {count|log|stats} [args]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "count" and len(sys.argv) >= 3:
        text = " ".join(sys.argv[2:])
        print(f"tokens: {count_tokens(text)}")
    elif cmd == "log" and len(sys.argv) >= 4:
        direction, text = sys.argv[2], " ".join(sys.argv[3:])
        n = log_call(direction, text)
        print(f"logged {n} tokens ({direction})")
    elif cmd == "stats":
        print(json.dumps(daily_stats(), indent=2, ensure_ascii=False))
    else:
        print(f"Unknown: {cmd}")
        sys.exit(1)
