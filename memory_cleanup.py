#!/usr/bin/env python3
"""
memory_cleanup.py - Auto-compress memory files when approaching limit

Reads MEMORY.md and USER.md, moves long content to notes/, replaces with pointers.
Runs daily via cron.

Token cost: 0 (Python only, no LLM)
"""
import os
import re
import json
import shutil
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
MEMORIES = HERMES / "memories"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
MEMORY_HISTORY = NOTES / "memory-archive.md"
MEMORY_HISTORY.parent.mkdir(parents=True, exist_ok=True)

# Read config
config = open(HERMES / "config.yaml").read()
m = re.search(r'memory_char_limit:\s*(\d+)', config)
MEMORY_LIMIT = int(m.group(1)) if m else 3000
m = re.search(r'user_char_limit:\s*(\d+)', config)
USER_LIMIT = int(m.group(1)) if m else 1800

# Thresholds (auto-compress when this % full)
WARN_PCT = 85
COMPRESS_PCT = 90


def get_size_chars(path):
    if not path.exists():
        return 0
    return len(path.read_text())


def compress_file(path, limit, kind):
    """If file exceeds threshold, move long sections to archive."""
    if not path.exists():
        return None
    content = path.read_text()
    size = len(content)
    pct = (size / limit) * 100
    result = {
        "file": path.name,
        "kind": kind,
        "before": size,
        "limit": limit,
        "pct": pct,
        "action": None,
    }
    if pct < COMPRESS_PCT:
        result["action"] = "ok"
        return result

    # Above threshold — archive oldest sections
    sections = content.split("§")
    sections = [s.strip() for s in sections if s.strip()]
    # Keep top 5 most recent (assume newest are at end)
    keep = sections[-5:] if len(sections) > 5 else sections
    archived = sections[:-5] if len(sections) > 5 else []

    if not archived:
        result["action"] = "no_compress_needed"
        return result

    # Write archived to history
    with open(MEMORY_HISTORY, "a") as f:
        f.write(f"\n\n## Archived from {path.name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        for a in archived:
            f.write(f"§ {a}\n\n")

    # Replace file with kept sections
    new_content = "\n\n§\n".join(keep)
    if not new_content.startswith("§ "):
        new_content = "§\n" + new_content
    path.write_text(new_content)

    result["after"] = len(new_content)
    result["archived_sections"] = len(archived)
    result["action"] = "compressed"
    return result


def main():
    print(f"🧹 Memory Cleanup — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    results = []
    for fname, limit, kind in [
        ("MEMORY.md", MEMORY_LIMIT, "memory"),
        ("USER.md", USER_LIMIT, "user"),
    ]:
        path = MEMORIES / fname
        size = get_size_chars(path)
        pct = (size / limit) * 100
        status = "🟢" if pct < WARN_PCT else ("🟡" if pct < COMPRESS_PCT else "🔴")
        print(f"  {status} {fname}: {size}/{limit} ({pct:.0f}%)")
        if pct >= COMPRESS_PCT:
            r = compress_file(path, limit, kind)
            if r and r["action"] == "compressed":
                print(f"      → compressed: {r['before']}→{r['after']} ({r['archived_sections']} sections archived)")
            results.append(r)

    # Save log
    log = CACHE / "memory_cleanup_log.json"
    log.write_text(json.dumps({
        "ran_at": datetime.now().isoformat(),
        "results": results,
    }, indent=2, default=str))
    print(f"\n📄 Log: {log}")
    if not results:
        print("✅ All memory files healthy.")


if __name__ == "__main__":
    main()
