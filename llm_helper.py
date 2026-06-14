#!/usr/bin/env python3
"""
llm_helper.py - Shared TokenRouter LLM call with optional Headroom compression

Single function to call TokenRouter. Uses reasoning_effort=low by default.
Cost: ~$0.0001/call (M3 cheap).

Usage:
    from llm_helper import llm_call
    result = llm_call("Your prompt", max_tokens=300)

    # With headroom compression (default ON for prompts > 500 chars)
    from llm_helper import llm_call_hr
    result = llm_call_hr("Your prompt with long log output", max_tokens=300)
"""
import json
import subprocess
from pathlib import Path

HERMES = Path.home() / ".hermes"
KEY_FILE = HERMES / "config" / "tokenrouter.key"
API_URL = "https://api.tokenrouter.com/v1/chat/completions"
MODEL = "MiniMax-M3"

# Headroom stats file
HR_STATS = HERMES / "cache" / "headroom_stats.json"
HR_STATS.parent.mkdir(parents=True, exist_ok=True)


def _record_hr_stat(tokens_before: int, tokens_after: int, transforms: list):
    """Record headroom compression stat."""
    try:
        stats = json.loads(HR_STATS.read_text()) if HR_STATS.exists() else {
            "calls": 0, "tokens_before": 0, "tokens_after": 0
        }
    except Exception:
        stats = {"calls": 0, "tokens_before": 0, "tokens_after": 0}
    stats["calls"] += 1
    stats["tokens_before"] += tokens_before
    stats["tokens_after"] += tokens_after
    if "transforms_used" not in stats:
        stats["transforms_used"] = {}
    for t in transforms:
        stats["transforms_used"][t] = stats["transforms_used"].get(t, 0) + 1
    HR_STATS.write_text(json.dumps(stats, indent=2))


def _get_token_estimate(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


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


def llm_call_hr(prompt, max_tokens=300, effort="low", timeout=30, force_compress=False):
    """
    LLM call with headroom compression for large prompts.
    - Auto-compresses if prompt > 500 chars
    - Records compression stats to ~/.hermes/cache/headroom_stats.json
    - Falls back to plain llm_call if headroom fails

    Returns: (response_text, stats_dict) or (response_text, None) if no compression
    """
    use_compress = force_compress or len(prompt) > 500
    if not use_compress:
        return llm_call(prompt, max_tokens, effort, timeout), None

    try:
        from headroom import compress
    except ImportError:
        return llm_call(prompt, max_tokens, effort, timeout), None

    # Compress user message
    messages = [{"role": "user", "content": prompt}]
    tokens_before = _get_token_estimate(prompt)
    result = compress(messages, model="claude-sonnet-4-5-20250929", compress_user_messages=True)
    tokens_after = result.tokens_after
    compressed_prompt = result.messages[0]["content"]
    # Record stat
    _record_hr_stat(tokens_before, tokens_after, result.transforms_applied)
    # Send compressed
    if not KEY_FILE.exists():
        return None, None
    api_key = KEY_FILE.read_text().strip()
    try:
        curl_result = subprocess.run([
            "curl", "-s", "-X", "POST", API_URL,
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": compressed_prompt}],
                "max_tokens": max_tokens,
                "reasoning_effort": effort,
            }),
        ], capture_output=True, text=True, timeout=timeout)
        if curl_result.returncode == 0 and curl_result.stdout:
            data = json.loads(curl_result.stdout)
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return text, {
                "tokens_before": tokens_before,
                "tokens_after": tokens_after,
                "saved": tokens_before - tokens_after,
                "ratio": (1 - tokens_after / max(tokens_before, 1)) * 100,
                "transforms": result.transforms_applied,
            }
    except Exception as e:
        return f"Error: {e}", None
    return None, None


def get_hr_stats() -> dict:
    """Get cumulative headroom stats."""
    if not HR_STATS.exists():
        return {"calls": 0, "tokens_before": 0, "tokens_after": 0, "savings_pct": 0}
    stats = json.loads(HR_STATS.read_text())
    before = stats.get("tokens_before", 0)
    after = stats.get("tokens_after", 0)
    stats["savings_pct"] = (1 - after / max(before, 1)) * 100 if before > 0 else 0
    return stats


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        s = get_hr_stats()
        print(f"📊 Headroom stats:")
        print(f"   Calls: {s.get('calls', 0)}")
        print(f"   Tokens before: {s.get('tokens_before', 0):,}")
        print(f"   Tokens after: {s.get('tokens_after', 0):,}")
        print(f"   Savings: {s.get('savings_pct', 0):.1f}%")
        print(f"   Transforms: {s.get('transforms_used', {})}")
    else:
        # Test
        r = llm_call("Say 'OK' in 5 words", max_tokens=20)
        print(f"Test: {r}")
