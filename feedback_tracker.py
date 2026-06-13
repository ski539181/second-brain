#!/usr/bin/env python3
"""
feedback_tracker.py - Track which responses are useful

Records:
- Response text
- User reaction (✅/❌/neutral)
- Topic/category

Aggregates: which response types get positive feedback.
Output: ~/.hermes/feedback/{date}.json
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
FEEDBACK_DIR = HERMES / "feedback"
FEEDBACK_DIR.mkdir(exist_ok=True)
CACHE = HERMES / "cache"
FEEDBACK_LOG = CACHE / "feedback.jsonl"


def log_feedback(response_text, signal, topic=None, note_id=None):
    """Log a single feedback event."""
    entry = {
        "ts": datetime.now().isoformat(),
        "signal": signal,  # "positive", "negative", "neutral"
        "topic": topic or "unknown",
        "note_id": note_id,
        "length": len(response_text),
        "has_code": "```" in response_text,
        "has_bullets": bool(re.search(r"^[\-\*]\s", response_text, re.MULTILINE)),
        "has_emoji": bool(re.search(r"[\U0001F300-\U0001F9FF]", response_text)),
        "has_thai": bool(re.search(r"[\u0E00-\u0E7F]", response_text)),
    }
    with FEEDBACK_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def analyze():
    """Analyze feedback patterns."""
    if not FEEDBACK_LOG.exists():
        return {"total": 0}
    
    entries = []
    for line in FEEDBACK_LOG.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    
    if not entries:
        return {"total": 0}
    
    total = len(entries)
    signals = Counter(e["signal"] for e in entries)
    topics = Counter(e["topic"] for e in entries)
    
    # Pattern analysis
    pos = [e for e in entries if e["signal"] == "positive"]
    neg = [e for e in entries if e["signal"] == "negative"]
    
    def avg_field(field, group):
        if not group:
            return 0
        return sum(e.get(field, 0) for e in group) / len(group)
    
    insights = {
        "total": total,
        "signals": dict(signals),
        "top_topics": dict(topics.most_common(5)),
        "positive_avg_length": avg_field("length", pos),
        "negative_avg_length": avg_field("length", neg),
        "positive_has_code_pct": (
            sum(1 for e in pos if e.get("has_code")) / len(pos) * 100 if pos else 0
        ),
        "negative_has_code_pct": (
            sum(1 for e in neg if e.get("has_code")) / len(neg) * 100 if neg else 0
        ),
        "positive_has_emoji_pct": (
            sum(1 for e in pos if e.get("has_emoji")) / len(pos) * 100 if pos else 0
        ),
    }
    return insights


def main():
    print(f"💬 Feedback Tracker — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    # Demo entries
    demo_responses = [
        ("✅ Good response", "positive", "scraper"),
        ("❌ Not helpful", "negative", "memory"),
        ("✅ Nice", "positive", "scraper"),
        ("✅ Clear", "positive", "cron"),
    ]
    for text, signal, topic in demo_responses:
        log_feedback(text, signal, topic=topic)
        print(f"  Logged: {signal} - {topic}")
    
    # Analyze
    insights = analyze()
    print(f"\n📊 Total feedback: {insights['total']}")
    print(f"📈 Signals: {insights.get('signals', {})}")
    if insights.get("top_topics"):
        print(f"🏷️ Top topics: {insights['top_topics']}")
    if insights.get("positive_avg_length"):
        print(f"📏 Avg length (positive): {insights['positive_avg_length']:.0f}")
    if insights.get("positive_has_code_pct"):
        print(f"💻 Code in positive: {insights['positive_has_code_pct']:.0f}%")
    
    # Save report
    out = FEEDBACK_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(insights, indent=2, default=str))
    print(f"\n📄 Saved: {out}")
    return 0


if __name__ == "__main__":
    exit(main())
