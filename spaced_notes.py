#!/usr/bin/env python3
"""
spaced_notes.py - Spaced repetition for notes (prevent forgetting)

Picks notes that haven't been reviewed in N days,
generates recall questions, tracks success.

Output: ~/.hermes/recall/{date}.md
"""
import json
import re
import random
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
RECALL_DIR = HERMES / "recall"
RECALL_DIR.mkdir(exist_ok=True)


def get_note_titles():
    titles = {}
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            text = f.read_text()
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            if m:
                titles[m.group(1).strip()] = f
        except Exception:
            pass
    return titles


def load_state():
    f = CACHE / "spaced_notes.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"notes": {}, "last_run": None}


def save_state(state):
    f = CACHE / "spaced_notes.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(state, indent=2, default=str))


def find_recall_targets(titles, state, limit=3):
    """Find notes due for recall (interval passed)."""
    now = datetime.now()
    targets = []
    for title, fp in titles.items():
        s = state["notes"].get(title, {})
        interval = s.get("interval_days", 1)  # start at 1 day
        last = s.get("last_recall")
        if last:
            last_dt = datetime.fromisoformat(last)
            if (now - last_dt).days < interval:
                continue
        # Pick it
        targets.append((title, fp, interval))
    random.seed(now.strftime("%Y%m%d"))
    random.shuffle(targets)
    return targets[:limit]


def generate_questions(text, title, count=2):
    """Generate recall questions from note text."""
    questions = []
    # Q1: 1-line summary
    questions.append(f"📌 '{title}' — สรุปสั้นๆ 1 บรรทัด")
    # Q2: pick concept from content
    words = re.findall(r"\b[A-Z][a-zA-Z]{4,}\b", text)
    if words:
        concept = random.choice(words)
        questions.append(f"🔑 '{concept}' คืออะไร? (อธิบาย 1-2 ประโยค)")
    # Q3: application
    questions.append(f"🛠️ ใช้ '{title}' ในงานจริงยังไง? (1 example)")
    return questions[:count]


def main():
    print(f"🔄 Spaced Notes Recall — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    titles = get_note_titles()
    state = load_state()
    targets = find_recall_targets(titles, state, limit=3)
    
    if not targets:
        print("✅ No notes due for recall. All up-to-date.")
        return 0
    
    print(f"📚 Found {len(targets)} notes for recall")
    
    lines = []
    lines.append(f"# 🔄 Spaced Recall — {datetime.now().strftime('%Y-%m-%d')}\n")
    lines.append(f"**Strategy:** Recall + check. If pass → interval × 2. If fail → interval ÷ 2.\n")
    
    for title, fp, interval in targets:
        print(f"  • {title}  (interval: {interval}d)")
        try:
            text = fp.read_text()[:2000]
        except Exception:
            continue
        questions = generate_questions(text, title)
        lines.append(f"\n## 📄 {title}")
        lines.append(f"- **Interval:** {interval} day(s)")
        lines.append(f"- **File:** `{fp.name}`")
        lines.append(f"\n### ❓ Recall these:\n")
        for q in questions:
            lines.append(f"1. {q}")
        lines.append(f"\n### ✅ Mark after answering:\n")
        lines.append(f"- [ ] Pass (interval → {interval*2}d)")
        lines.append(f"- [ ] Fail (interval → {max(1, interval//2)}d)")
        
        # Update state — mark as seen
        state["notes"][title] = {
            "last_recall": datetime.now().isoformat(),
            "interval_days": interval,
            "file": fp.name,
        }
    
    state["last_run"] = datetime.now().isoformat()
    save_state(state)
    
    out = RECALL_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    out.write_text("\n".join(lines))
    print(f"\n📄 Saved: {out}")
    print(f"💡 Answer questions, then mark Pass/Fail in the file")
    return 0


if __name__ == "__main__":
    exit(main())
