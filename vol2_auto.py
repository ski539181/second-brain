#!/usr/bin/env python3
"""
vol2_auto.py - Auto-detect topic + consult vol2 (TRUE auto, not skill-only)
Detects 11 vol2 topics in user message via keyword matching.
Returns: matched topics, summaries, bug warnings.
Designed to be called by my response pipeline.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERMES = Path.home() / ".hermes"
INDEX = HERMES / "cache" / "vol2_index.json"
SCRIPT = HERMES / "scripts" / "vol2_index.py"

# Topic detection (Thai + English keywords)
TOPIC_KEYWORDS = {
    "raft": ["raft", "consensus", "leader election", "replication", "เลือก leader", "ลอการ์ทึม"],
    "lsm": ["lsm", "sstable", "memtable", "compaction", "wal", "log-structured"],
    "lock-free": ["lock-free", "cas ", "compare-exchange", "atomic", "mpsc", "spsc", "treiber", "aba"],
    "neural": ["neural", "autograd", "backprop", "adam optimizer", "gradient", "โครงข่าย"],
    "merkle": ["merkle", "sparse merkle", "inclusion proof", "verification tree"],
    "hyperloglog++": ["hyperloglog", "cardinality", "distinct count", "นับ unique"],
    "persistent": ["persistent data structure", "versioning", "segment tree", "kth smallest", "persistence"],
    "rope": ["rope", "persistent editor", "text tree", "string concat", "text editor", "undo", "redo"],
    "custom": ["dns resolver", "dns wire", "udp dns", "name compression"],
    "two-phase": ["two-phase", "2pl", "deadlock", "wait-for graph", "lock manager"],
    "actor": ["actor model", "mailbox", "supervision", "message passing", "fault tolerance"],
}


def detect_topics(text: str) -> list:
    """Detect vol2 topics mentioned in text."""
    text_lower = text.lower()
    matched = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(topic)
    return matched


def consult(topic: str) -> dict:
    """Get summary + bug info for a topic."""
    if not INDEX.exists():
        subprocess.run(["python3", str(SCRIPT), "--rebuild"], capture_output=True, timeout=5)
    idx = json.loads(INDEX.read_text())
    e = idx["entries"].get(topic, {})
    return {
        "topic": topic,
        "title": e.get("title", ""),
        "summary": e.get("summary", "")[:300],
        "has_bug": e.get("has_bug", False),
        "bug_note": e.get("bug_note", ""),
    }


def auto_check(user_text: str) -> dict:
    """Main entry: detect + consult in one call."""
    topics = detect_topics(user_text)
    if not topics:
        return {"matched": False, "topics": []}
    consultations = [consult(t) for t in topics[:3]]  # max 3 topics
    return {
        "matched": True,
        "topics": topics,
        "consultations": consultations,
    }


def format_for_prompt(result: dict) -> str:
    """Format consultations as a prompt addition."""
    if not result.get("matched"):
        return ""
    lines = ["\n💡 vol2 auto-consult:"]
    for c in result["consultations"]:
        bug = "🐛" if c["has_bug"] else "✅"
        lines.append(f"  {bug} {c['title']}")
        lines.append(f"     Pattern: {c['summary'][:150]}...")
        if c["has_bug"]:
            lines.append(f"     ⚠️  {c['bug_note']}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: vol2_auto.py <user message>")
        sys.exit(1)
    text = " ".join(sys.argv[1:])
    result = auto_check(text)
    if result["matched"]:
        print(f"🎯 Matched topics: {', '.join(result['topics'])}")
        print(format_for_prompt(result))
    else:
        print("No vol2 topics detected")


if __name__ == "__main__":
    main()
