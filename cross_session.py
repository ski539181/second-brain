#!/usr/bin/env python3
"""
cross_session.py - Cross-session knowledge analysis

Analyzes:
- Recent session messages (via session_search)
- Recurring topics (asked 3+ times)
- Gaps (topics asked but no note exists)
- Suggestions (which note to create/update)

Output: ~/.hermes/session_insights/{date}.md
"""
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"

# Optional LLM support
try:
    sys.path.insert(0, str(HERMES / "scripts"))
    from llm_helper import llm_call
    HAS_LLM = True
except Exception:
    HAS_LLM = False
NOTES = HERMES / "notes"
LOGS = HERMES / "logs"
INSIGHTS_DIR = HERMES / "session_insights"
INSIGHTS_DIR.mkdir(exist_ok=True)


def get_note_titles():
    titles = set()
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            text = f.read_text()
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            if m:
                titles.add(m.group(1).strip().lower())
        except Exception:
            pass
    return titles


def extract_topics_from_text(text, ngrams=(1, 2, 3)):
    """Extract key topics from text using n-grams."""
    # Remove common stopwords
    stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "i", "you", "we", "they", "he", "she", "it", "this", "that",
            "and", "or", "but", "if", "then", "so", "as", "do", "does",
            "did", "have", "has", "had", "will", "would", "could", "should",
            "can", "may", "might", "must", "shall", "not", "no", "yes",
            "my", "your", "our", "their", "his", "her", "its", "what",
            "which", "who", "when", "where", "why", "how", "than", "such",
            "ทำ", "ให้", "จะ", "คุณ", "ผม", "มัน", "เรา", "เขา", "เธอ",
            "ได้", "ไม่", "ใช่", "แล้ว", "ด้วย", "จาก", "สำหรับ", "ก็",
            "มี", "เป็น", "อยู่", "ที่", "นี้", "นั้น"}
    # Tokenize
    text = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in text.split() if w and len(w) > 2 and w not in stop]
    # Extract n-grams
    ngrams_found = Counter()
    for n in ngrams:
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i+n])
            ngrams_found[phrase] += 1
    return ngrams_found


def get_recent_user_messages():
    """Get user messages from recent sessions (heuristic from logs)."""
    # Use session_search via subprocess
    try:
        result = subprocess.run(
            ["hermes", "session", "list", "--limit", "20", "--json"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:
        pass
    return []


def find_recurring_topics(messages, threshold=3):
    """Find topics that appear in multiple messages."""
    topic_counter = Counter()
    for msg in messages:
        text = msg.get("content", "") if isinstance(msg, dict) else str(msg)
        topics = extract_topics_from_text(text, ngrams=(2, 3))
        for t, n in topics.items():
            if n >= 2:  # at least 2 occurrences in one message
                topic_counter[t] += 1
    # Filter: must appear in 3+ different messages
    recurring = {t: c for t, c in topic_counter.items() if c >= threshold}
    return Counter(recurring).most_common(15)


def find_gaps(recurring_topics, note_titles):
    """Find topics that are asked but no note exists."""
    gaps = []
    for topic, count in recurring_topics:
        # Check if any note title contains this topic
        found = any(topic in t for t in note_titles)
        if not found:
            gaps.append((topic, count))
    return gaps[:10]


def suggest_actions(recurring, gaps):
    """Generate actionable suggestions."""
    actions = []
    
    # 1. Top recurring topics → make index note
    for topic, count in recurring[:5]:
        if count >= 5:
            actions.append(f"📌 '{topic}' ถามบ่อย ({count} ครั้ง) → ควรมี index note")
    
    # 2. Gaps → create note
    for topic, count in gaps[:5]:
        actions.append(f"❓ '{topic}' ถามแต่ไม่มี note ({count} ครั้ง) → สร้าง note ใหม่")
    
    return actions


def llm_synthesize_topics(recurring, gaps, existing_notes):
    """Use LLM to find deeper topic connections (~$0.0001)."""
    rec_str = ", ".join(f"{t}(×{c})" for t, c in recurring)
    gap_str = ", ".join(f"'{t}'" for t, c in gaps) if gaps else "none"
    note_str = ", ".join(existing_notes[:10])
    prompt = f"""Recurring topics user asks: {rec_str}
Knowledge gaps (no note yet): {gap_str}
Existing notes: {note_str}

What 1-2 patterns connect these? What's the most valuable next note to write?
Be concise, actionable, Thai/English mix, max 80 words."""
    return llm_call(prompt, max_tokens=200)


def main():
    print(f"🌐 Cross-Session Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    note_titles = get_note_titles()
    print(f"📚 Found {len(note_titles)} note titles")
    
    # Get messages
    messages = get_recent_user_messages()
    print(f"💬 Loaded {len(messages)} recent messages")
    
    if not messages:
        # Fallback: analyze our own session log
        # Look at this session's user messages from stdin/stdout
        print("⚠️ No session data — using file-based fallback")
        # Read journal/notes for content
        text_corpus = ""
        for f in NOTES.rglob("*.md"):
            if "archive" not in str(f):
                try:
                    text_corpus += f.read_text()[:500] + "\n"
                except Exception:
                    pass
        topics = extract_topics_from_text(text_corpus, ngrams=(2, 3))
        recurring = topics.most_common(10)
    else:
        recurring = find_recurring_topics(messages)
    
    gaps = find_gaps([(t, c) for t, c in recurring], note_titles)
    actions = suggest_actions(recurring, gaps)
    
    print(f"\n🔍 Top recurring: {len(recurring)} topics")
    if recurring[:5]:
        for t, c in recurring[:5]:
            print(f"  • '{t}' (×{c})")
    print(f"\n❓ Gaps: {len(gaps)} topics with no note")
    if gaps[:3]:
        for t, c in gaps[:3]:
            print(f"  • '{t}' (×{c})")
    
    # Save
    out_md = INSIGHTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    md = f"# 🌐 Cross-Session Insights — {datetime.now().strftime('%Y-%m-%d')}\n\n"
    md += f"**Notes:** {len(note_titles)} | **Messages:** {len(messages)}\n\n"
    md += "## 🔁 Top recurring topics\n\n"
    for t, c in recurring[:10]:
        md += f"- **{t}** (×{c})\n"
    md += "\n## ❓ Gaps (no note exists)\n\n"
    if gaps:
        for t, c in gaps:
            md += f"- '{t}' (×{c})\n"
    else:
        md += "_(none — all topics covered)_\n"
    md += "\n## 🎯 Suggested actions\n\n"
    if actions:
        for a in actions:
            md += f"- {a}\n"
    else:
        md += "_(no immediate actions needed)_\n"

    # LLM synthesis — find deeper connections
    if HAS_LLM and "--llm" in sys.argv and recurring:
        # note_titles might be a set
        nt_list = list(note_titles) if not isinstance(note_titles, list) else note_titles
        synth = llm_synthesize_topics(recurring[:5], gaps[:3], nt_list[:10])
        if synth:
            md += f"\n## 🤖 LLM Cross-Session Synthesis\n\n{synth}\n"
    out_md.write_text(md)
    
    out_json = INSIGHTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    out_json.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "note_count": len(note_titles),
        "recurring": dict(recurring[:20]),
        "gaps": dict(gaps),
    }, indent=2, default=str))
    
    print(f"\n📄 Saved: {out_md}")
    print(f"📄 Saved: {out_json}")
    return 0


if __name__ == "__main__":
    exit(main())
