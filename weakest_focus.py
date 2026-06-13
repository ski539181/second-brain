#!/usr/bin/env python3
"""
weakest_focus.py - Deliberate practice: target lowest mastery skill

Reads practice queue, finds lowest mastery challenges,
generates 1 targeted exercise for each.

Output: ~/.hermes/practice/today.md
"""
import json
import re
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
NOTES = HERMES / "notes"
PRACTICE_DIR = HERMES / "practice"
PRACTICE_DIR.mkdir(exist_ok=True)


def load_queue():
    f = CACHE / "practice-queue.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


def find_lowest_mastery(queue, limit=3):
    """Find challenges with lowest mastery score."""
    challenges = queue.get("challenges", {})
    ranked = sorted(
        challenges.items(),
        key=lambda x: (x[1].get("mastery", 0), -x[1].get("attempts", 0))
    )
    return [(int(k), v) for k, v in ranked[:limit]]


def load_challenge(pid):
    """Load a challenge from the markdown file."""
    md = NOTES / "coding-challenges-45.md"
    if not md.exists():
        return None
    text = md.read_text()
    # Find section for this PID
    pattern = rf"###\s*{pid}\.\s+(.+?)(?=###\s+\d+\.|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(0)
    return None


def generate_exercise(challenge_text, title):
    """Generate 1 targeted exercise based on the challenge."""
    # Extract bug type from title
    bug_types = {
        "default": "เขียน 2-3 test cases ที่จะ break ถ้าใช้ default arg แบบ mutable",
        "binding": "สร้าง 3 closures ที่ต้อง capture ค่าต่างกัน — predict output",
        "Generator": "เขียน generator ที่ใช้ 2 ครั้ง — หา bug",
        "None": "เขียน compare pattern 3 แบบที่ None เป็นปัญหา",
        "interning": "ทำนายว่า string ไหน share memory",
        "float": "เขียน 5 floating point calculations — ใช้ math.isclose ตรวจ",
        "Dict": "modify dict ขณะ iterate — ทำนาย RuntimeError",
        "multiply": "สร้าง 2D array 2 วิธี — หา reference vs copy",
        "tuple": "สร้าง dict key ที่เป็น tuple (immutable)",
        "encoding": "decode bytes vs str — หา UnicodeDecodeError",
        "Slicing": "predict slicing [start:stop:step] 10 cases",
        "sort": "sort list of tuples, list of dicts, list of mixed",
        "args": "modify *args — explain when it's safe",
        "Walrus": "เขียน 3 use cases ของ := operator",
        "Star": "ใช้ * ใน function call 5 patterns",
    }
    for key, exercise in bug_types.items():
        if key.lower() in title.lower() or key.lower() in challenge_text.lower():
            return exercise
    return f"อธิบาย '{title}' ด้วยตัวอย่างจริง 3 cases — predict output, run, verify"


def main():
    print(f"🎯 Weakest Skill Focus — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    queue = load_queue()
    if not queue:
        print("❌ No practice queue found. Run: practice_queue.py update")
        return 1
    
    lowest = find_lowest_mastery(queue)
    if not lowest:
        print("❌ No challenges in queue")
        return 1
    
    print(f"📊 Found {len(lowest)} weakest challenges")
    lines = []
    lines.append(f"# 🎯 Today's Practice — {datetime.now().strftime('%Y-%m-%d')}\n")
    lines.append(f"**Focus:** {len(lowest)} weakest skills (deliberate practice)\n")
    lines.append("\n## 📋 Targeted Exercises\n")
    
    for pid, data in lowest:
        mastery = data.get("mastery", 0)
        attempts = data.get("attempts", 0)
        status = data.get("status", "new")
        print(f"  • Q{pid}: mastery={mastery}%, attempts={attempts}, status={status}")
        
        # Load challenge
        challenge_text = load_challenge(pid) or ""
        title_match = re.search(rf"###\s*{pid}\.\s+(.+?)$", challenge_text, re.MULTILINE)
        title = title_match.group(1) if title_match else f"Challenge {pid}"
        
        # Generate exercise
        exercise = generate_exercise(challenge_text, title)
        
        lines.append(f"\n### Q{pid}: {title}")
        lines.append(f"- **Mastery:** {mastery}% | **Attempts:** {attempts} | **Status:** {status}")
        lines.append(f"- **Exercise:** {exercise}")
        lines.append(f"- **Action:** run `python3 ~/.hermes/scripts/practice_queue.py practice {pid}`")
    
    lines.append("\n## 🎯 Why these?\n")
    lines.append("These have the lowest mastery + fewest attempts. ")
    lines.append("Focus on these = faster progress (Pareto principle).\n")
    lines.append("\n## ⏱️ Time budget\n")
    lines.append(f"~15-20 minutes/day → 1 exercise each = 3 sessions/week\n")
    
    out = PRACTICE_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    out.write_text("\n".join(lines))
    print(f"\n📄 Saved: {out}")
    return 0


if __name__ == "__main__":
    exit(main())
