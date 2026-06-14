#!/usr/bin/env python3
"""
vol2_index.py - Index vol2 by topic, expose safe lookup
- Parse vol2, extract topics + thinking patterns
- Store summaries (not full code) for quick reference
- Track known bugs per entry
- Lookup: vol2_index.py "raft" → returns topic summary + code stub + bugs
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
VOL2_PATH = HERMES / "cache" / "documents" / "doc_e34497812434_advanced-coding-dataset-20-vol2.md"
INDEX_PATH = CACHE / "vol2_index.json"

# Known bugs from my analysis
KNOWN_BUGS = {
    "raft": "Demo: `new InProcNet().forNode?.(id)` ไม่ได้ใช้ — ลบบรรทัดนี้ก่อน",
    "lsm": "Compaction ไม่ trigger ต่อเนื่อง L1→L2 — เพิ่ม recursive call",
    "lock-free": "ABA: doc บอก version counter แต่ code ไม่มี — เพิ่ม tagged pointer",
    "nn": "Adam bias correction ผิด, Add backward assume row vector",
    "pst": "`_push`: `(l+r>>1)+1` precedence bug → ใส่ parens",
    "actor": "`_stop` children: `cr.id` ไม่มี attribute นี้",
}

def parse_vol2():
    """Parse vol2 into indexed topics."""
    if not VOL2_PATH.exists():
        return {}
    text = VOL2_PATH.read_text()
    # Find entries: ENTRY 001 — Topic
    entries = {}
    pattern = re.compile(r'## ENTRY (\d+) — (.+?)\n', re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        num = m.group(1)
        title = m.group(2).strip()
        # Get content until next entry
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        content = text[start:end]
        # Extract topic keywords
        topic_key = title.lower().split()[0]  # raft, lsm, etc.
        # Extract first 200 chars of thinking as summary
        think_match = re.search(r'### \[Thinking & Logic\](.+?)(?=###|\Z)', content, re.DOTALL)
        summary = ""
        if think_match:
            # Get first 3 bullet points or 300 chars
            t = think_match.group(1)[:600]
            summary = re.sub(r'\n+', ' ', t).strip()[:400]
        entries[topic_key] = {
            "num": num,
            "title": title,
            "summary": summary,
            "size": len(content),
            "has_bug": topic_key in KNOWN_BUGS,
            "bug_note": KNOWN_BUGS.get(topic_key, ""),
        }
    return entries

def build_index():
    """Build and save index."""
    entries = parse_vol2()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps({
        "generated": datetime.now().isoformat(),
        "count": len(entries),
        "entries": entries,
    }, indent=2, ensure_ascii=False))
    return entries

def lookup(topic: str, full: bool = False):
    """Look up topic. If full=True, print full entry from vol2."""
    if not INDEX_PATH.exists():
        build_index()
    idx = json.loads(INDEX_PATH.read_text())
    entries = idx["entries"]
    # Fuzzy match
    matches = [k for k in entries if topic.lower() in k.lower()]
    if not matches:
        print(f"❌ Topic '{topic}' not found. Try: {', '.join(entries.keys())}")
        return None
    key = matches[0]
    e = entries[key]
    print(f"📚 Entry {e['num']} — {e['title']}\n")
    print(f"📝 Summary:\n   {e['summary'][:300]}...")
    print(f"\n📊 Stats: {e['size']} chars in full entry")
    if e["has_bug"]:
        print(f"\n⚠️  KNOWN BUG: {e['bug_note']}")
        print(f"   🛡️  Don't copy code directly — extract pattern only")
    if full and VOL2_PATH.exists():
        # Find and print full entry
        text = VOL2_PATH.read_text()
        m = re.search(rf'## ENTRY {e["num"]} — .+?\n(.+?)(?=## ENTRY|\Z)', text, re.DOTALL)
        if m:
            print(f"\n" + "="*60)
            print(m.group(0)[:2000] + ("..." if len(m.group(0)) > 2000 else ""))
    return e

def list_all():
    """List all topics with bug warnings."""
    if not INDEX_PATH.exists():
        build_index()
    idx = json.loads(INDEX_PATH.read_text())
    print(f"📚 vol2 Index — {idx['count']} topics ({idx['generated'][:10]})\n")
    for k, e in idx["entries"].items():
        bug = "🐛" if e["has_bug"] else "✅"
        print(f"  {bug} {k:15} — {e['title']}")

def main():
    if len(sys.argv) < 2:
        list_all()
        return
    cmd = sys.argv[1]
    if cmd == "--list":
        list_all()
    elif cmd == "--rebuild":
        entries = build_index()
        print(f"✅ Rebuilt: {len(entries)} topics")
    else:
        full = "--full" in sys.argv
        lookup(cmd, full=full)

if __name__ == "__main__":
    main()
