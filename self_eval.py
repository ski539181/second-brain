#!/usr/bin/env python3
"""
self_eval.py - Self-evaluation of LLM responses

Scores my own responses on:
- Addressed question
- Has code/example
- Concise (not too long)
- Thai/English mix (user preference)
- Actionable

Output: ~/.hermes/eval/{date}.json + .md
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
LOGS = HERMES / "logs"
EVAL_DIR = HERMES / "eval"
EVAL_DIR.mkdir(exist_ok=True)

# Optional LLM support
try:
    sys.path.insert(0, str(HERMES / "scripts"))
    from llm_helper import llm_call
    HAS_LLM = True
except Exception:
    HAS_LLM = False


def score_response(text):
    """Score a response 0-100."""
    score = 0
    feedback = []
    
    # 1. Length check (10-3000 chars ideal)
    length = len(text)
    if 10 <= length <= 3000:
        score += 20
    elif length > 3000:
        score += 10
        feedback.append("⚠️ Too long (>3000 chars)")
    else:
        feedback.append("⚠️ Too short (<10 chars)")
    
    # 2. Has code or example
    if "```" in text or "    " in text:  # code block or indented
        score += 20
    else:
        feedback.append("ℹ️ No code block (consider adding)")
    
    # 3. Has bullets or structure
    if re.search(r"^[\-\*]\s", text, re.MULTILINE) or re.search(r"^##", text, re.MULTILINE):
        score += 15
    else:
        feedback.append("ℹ️ No bullets/headers (hard to scan)")
    
    # 4. Has emoji or visual indicator
    if re.search(r"[\U0001F300-\U0001F9FF]", text):
        score += 10
    else:
        feedback.append("ℹ️ No emoji (less scannable)")
    
    # 5. Thai/English mix
    has_thai = bool(re.search(r"[\u0E00-\u0E7F]", text))
    has_eng = bool(re.search(r"[a-zA-Z]{3,}", text))
    if has_thai and has_eng:
        score += 15
    elif has_thai or has_eng:
        score += 8
    
    # 6. Has actionable items (commit, run, install, etc.)
    if re.search(r"\b(run|install|commit|push|cron|edit|add|create)\b", text, re.IGNORECASE):
        score += 10
    else:
        feedback.append("ℹ️ No actionable steps")
    
    # 7. Has question (clarify or follow-up)
    if "?" in text or "?" in text:
        score += 5
    
    # 8. No error patterns
    if "Traceback" in text or "ERROR:" in text:
        score -= 20
        feedback.append("❌ Contains error/traceback")
    
    return {
        "score": max(0, min(100, score)),
        "length": length,
        "feedback": feedback,
    }


def evaluate_recent_logs():
    """Look for recent LLM output to evaluate."""
    token_log = LOGS / "tokens.jsonl"
    if not token_log.exists():
        return []
    
    # Read recent output entries
    entries = []
    for line in token_log.read_text().splitlines()[-50:]:
        try:
            e = json.loads(line)
            if e.get("direction") == "output" and e.get("text"):
                entries.append(e)
        except Exception:
            pass
    
    return entries


def llm_meta_analysis(results, avg):
    """Use LLM to find patterns in self-eval scores."""
    top_feedback = []
    for r in results[:5]:
        top_feedback.extend(r.get("feedback", [])[:2])
    if not top_feedback:
        return None
    prompt = f"""Self-eval avg score: {avg:.1f}/100

Top feedback patterns:
{chr(10).join('- ' + f for f in top_feedback[:8])}

What 1-2 specific changes would improve my response quality?
Be actionable, max 80 words, Thai/English OK."""
    return llm_call(prompt, max_tokens=200)


def main():
    print(f"🎯 Self-Evaluation — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    entries = evaluate_recent_logs()
    if not entries:
        print("ℹ️ No recent LLM outputs to evaluate. Use after LLM call.")
        # Demo: evaluate a sample
        sample = "✅ Test: this is good. ```code```. Has bullet:\n- item\n- item. 🎯 Run `python3 test.py`"
        s = score_response(sample)
        print(f"\n📊 Sample evaluation: {s['score']}/100")
        return 0
    
    print(f"📋 Evaluating {len(entries)} recent outputs")
    
    total_score = 0
    results = []
    for e in entries:
        text = e.get("text", "")
        s = score_response(text)
        total_score += s["score"]
        results.append({"id": e.get("id", "?"), **s})
    
    avg = total_score / len(results) if results else 0
    print(f"📊 Average score: {avg:.1f}/100")
    
    # Save
    out_json = EVAL_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    out_json.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "average_score": avg,
        "results": results,
    }, indent=2, default=str))
    
    # Markdown summary
    out_md = EVAL_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    md = f"# 🎯 Self-Evaluation — {datetime.now().strftime('%Y-%m-%d')}\n\n"
    md += f"**Average score:** {avg:.1f}/100\n\n"
    md += f"**Evaluated:** {len(results)} outputs\n\n"
    md += "## 📊 Top improvements to make:\n\n"
    # Aggregate feedback
    all_feedback = []
    for r in results:
        all_feedback.extend(r.get("feedback", []))
    from collections import Counter
    fb_count = Counter(all_feedback)
    for fb, n in fb_count.most_common(5):
        md += f"- {fb}  (×{n})\n"

    # LLM meta-analysis — 1 call to find patterns (--llm flag)
    if HAS_LLM and "--llm" in sys.argv and results:
        meta = llm_meta_analysis(results, avg)
        if meta:
            md += f"\n## 🤖 LLM Meta-Analysis\n\n{meta}\n"
    out_md.write_text(md)
    
    print(f"\n📄 Saved: {out_json}")
    print(f"📄 Saved: {out_md}")
    return 0


if __name__ == "__main__":
    exit(main())
