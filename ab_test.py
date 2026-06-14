#!/usr/bin/env python3
"""
ab_test.py - A/B test: web-scraper context vs no context
- 5 real questions
- Score both responses
- Report diff
- Time: ~10 min
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, '/root/.hermes/scripts')
from llm_helper import llm_call
try:
    from llm_helper import HAS_LLM
except ImportError:
    HAS_LLM = True

# Load web-scraper dataset (abbreviated)
DS_PATH = Path('/root/.hermes/cache/documents/doc_e16cd0f14e3e_web-scraper-finetune-dataset.md')
DATASET = DS_PATH.read_text()[:8000] if DS_PATH.exists() else ""

QUESTIONS = [
    "เขียน circuit breaker pattern สำหรับ retry API calls",
    "อธิบาย state persistence pattern สำหรับ scraper",
    "เขียน exponential backoff ใน Node.js",
    "Playwright: handle Cloudflare challenge ยังไง",
    "เขียน atomic file write ใน Node.js",
]

# Scoring (simple heuristics)
def score(response: str) -> dict:
    code_lines = sum(1 for l in response.split('\n') if l.strip().startswith(('def ', 'class ', 'const ', 'let ', 'function ', 'import ', 'export ', 'await ', 'return ')))
    has_thai = any('\u0E00' <= c <= '\u0E7F' for c in response)
    has_code = '```' in response or 'function' in response
    has_explanation = len(response) > 200
    return {
        "length": len(response),
        "code_lines": code_lines,
        "has_code": has_code,
        "has_thai": has_thai,
        "score": min(100, code_lines * 5 + (50 if has_code else 0) + (20 if has_thai else 0) + (10 if has_explanation else 0))
    }


def main():
    t0 = time.time()
    print(f"🧪 A/B Test — web-scraper context effect\n")
    print(f"Dataset: {len(DATASET)} chars | Questions: {len(QUESTIONS)} | LLM: {HAS_LLM}\n")
    if not HAS_LLM:
        print("❌ LLM not available")
        return

    results = []
    for i, q in enumerate(QUESTIONS, 1):
        # A: no context
        a_resp = llm_call(f"Answer concisely in Thai+code:\n\n{q}", max_tokens=400)
        # B: with web-scraper context
        b_resp = llm_call(f"Use this reference style/patterns:\n\n{DATASET[:4000]}\n\n---\nAnswer concisely in Thai+code:\n\n{q}", max_tokens=400)
        a_score = score(a_resp)
        b_score = score(b_resp)
        delta = b_score["score"] - a_score["score"]
        winner = "B" if delta > 0 else ("A" if delta < 0 else "TIE")
        results.append((q, a_score, b_score, delta, winner))
        print(f"  Q{i}: {q[:50]}...")
        print(f"     A: {a_score['score']}/100 ({a_score['length']}c, {a_score['code_lines']} code)")
        print(f"     B: {b_score['score']}/100 ({b_score['length']}c, {b_score['code_lines']} code)")
        print(f"     Winner: {winner} (Δ {delta:+d})")
        print()
        if time.time() - t0 > 480:  # 8 min limit
            print("⏱️  Time limit reached, stopping")
            break

    # Summary
    a_total = sum(r[1]["score"] for r in results)
    b_total = sum(r[2]["score"] for r in results)
    a_wins = sum(1 for r in results if r[4] == "A")
    b_wins = sum(1 for r in results if r[4] == "B")
    ties = sum(1 for r in results if r[4] == "TIE")
    elapsed = time.time() - t0
    print(f"\n📊 Results ({elapsed:.0f}s):")
    print(f"  A total: {a_total} | B total: {b_total}")
    print(f"  A wins: {a_wins} | B wins: {b_wins} | Ties: {ties}")
    if b_total > a_total * 1.05:
        print(f"  ✅ B (with context) wins by {((b_total - a_total) / a_total * 100):.0f}%")
    elif a_total > b_total * 1.05:
        print(f"  ❌ A (no context) wins by {((a_total - b_total) / b_total * 100):.0f}%")
    else:
        print(f"  ⚖️  TIE — no significant difference")


if __name__ == "__main__":
    main()
