#!/usr/bin/env python3
"""
auto_reasoning.py — Auto-detect prompt complexity and set reasoning_effort

Concept: M3 (via TokenRouter) supports reasoning_effort param.
This script inspects the prompt and picks the right level automatically.

Usage:
  python3 auto_reasoning.py "your prompt here"
  echo "prompt" | python3 auto_reasoning.py
  python3 auto_reasoning.py --effort=high "your prompt"   # override

Effort levels:
  none   → simple/greeting (fast, save tokens)
  low    → short Q&A, status checks
  medium → normal questions, default
  high   → research, code, analysis, multi-step
"""
import sys, os, json, urllib.request, time, re, argparse

# Resolve API key from Hermes credential pool (sk-Ty6... key works for M3)
def get_api_key():
    """get_api_key - TODO: describe."""
    sys.path.insert(0, '/usr/local/lib/python3.14/dist-packages')
    from hermes_cli.auth import _load_auth_store
    store = _load_auth_store()
    for entries in store.get("credential_pool", {}).values():
        for e in entries:
            k = e.get("access_token", "")
            if k.startswith("sk-Ty6"):
                return k
    raise RuntimeError("No valid TokenRouter key found")

# Heuristic effort detection
LOW_KW = ["quick", "brief", "short", "tldr", "just", "เร็วๆ", "สั้นๆ", "แค่",
          "แปปเดียว", "ไม่ต้องยาว", "1 line", "บรรทัดเดียว", "hello", "hi ", "thanks",
          "ขอบคุณ", "ok", "ใช่", "ไม่ใช่", "yes", "no", "what is", "="]
HIGH_KW = ["research", "analyze", "analysis", "compare", "design", "debug",
           "implement", "code", "architecture", "refactor", "optimize", "explain",
           "วิเคราะห์", "เปรียบเทียบ", "เขียน", "อธิบาย", "แก้บั๊ก", "ออกแบบ",
           "refactor", "optimize", "implement", "สร้าง", "พัฒนา", "research"]

    """detect_effort - TODO: describe."""
def detect_effort(prompt: str) -> str:
    p = prompt.strip().lower()
    n = len(p)
    # Very short → none
    if n < 15:
        return "none"
    # Count keyword matches
    low_hits = sum(1 for kw in LOW_KW if kw in p)
    high_hits = sum(1 for kw in HIGH_KW if kw in p)
    # Long + keywords
    if high_hits >= 1 and n > 100:
        return "high"
    if high_hits >= 1:
        return "medium"
    if low_hits >= 1:
        return "low"
    # Length-based default
    if n < 60:
        return "low"
    if n < 200:
        return "medium"
    return "high"
        """call_m3 - TODO: describe."""

def call_m3(prompt: str, effort: str, model: str = "MiniMax-M3", timeout: int = 60):
    api_key = get_api_key()
    url = "https://api.tokenrouter.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "reasoning_effort": effort
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    dt = time.time() - t0
        """main - TODO: describe."""
    return data, dt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?", help="Prompt text (or pipe via stdin)")
    ap.add_argument("--effort", choices=["none", "low", "medium", "high"],
                    help="Override auto-detection")
    ap.add_argument("--json", action="store_true", help="JSON output only")
    ap.add_argument("--explain", action="store_true", help="Show detection reasoning")
    args = ap.parse_args()

    prompt = args.prompt or sys.stdin.read().strip()
    if not prompt:
        ap.error("Provide a prompt or pipe via stdin")

    effort = args.effort or detect_effort(prompt)
    data, dt = call_m3(prompt, effort)
    msg = data["choices"][0]["message"]
    content = msg.get("content", "") or ""
    usage = data.get("usage", {})

    # Strip visible thinking from output (keep clean answer)
    clean = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL).strip()
    if not clean:
        clean = content.strip()

    out = {
        "effort": effort,
        "time_s": round(dt, 2),
        "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "answer": clean
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"🎚️ effort={effort} | ⏱️ {out['time_s']}s | 🧠 rt={out['reasoning_tokens']}")
        print(f"💬 {clean}")
        if args.explain:
            print(f"\n[detection: prompt_len={len(prompt)}, effort={effort}]")

if __name__ == "__main__":
    main()
