#!/usr/bin/env python3
"""
quick_respond.py - Python bypass for mechanical queries (Option 1)

Skips LLM for queries that have deterministic answers.
Detects patterns and returns directly.

Usage:
    python3 quick_respond.py "<query>"
    # Returns: "BYPASS: <answer>" or None (if LLM needed)
"""

import re
import subprocess
import json
import os
import time
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
CACHE.mkdir(parents=True, exist_ok=True)


def q_time(q):
    """Time-related queries."""
    if re.search(r"เวลา|time|what time|กี่โมง|ตอนนี้", q, re.IGNORECASE):
        return datetime.now().strftime("%H:%M:%S")


def q_date(q):
    """Date queries."""
    if re.search(r"วันที่|date|วันอะไร|เมื่อวาน|พรุ่งนี้|today", q, re.IGNORECASE):
        thai_days = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
        thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
                       "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        now = datetime.now()
        day = thai_days[now.weekday()]
        month = thai_months[now.month - 1]
        return f"{day}ที่ {now.day} {month} {now.year + 543} ({now.strftime('%H:%M')})"


def q_memory(q):
    """Memory usage queries."""
    if re.search(r"memory|ความจำ|memories|จำได้", q, re.IGNORECASE):
        results = []
        for name, limit in [("MEMORY.md", 3000), ("USER.md", 1800)]:
            p = HERMES / "memories" / name
            if p.exists():
                size = len(p.read_text())
                pct = 100 * size / limit
                results.append(f"{name}: {pct:.0f}% ({size}/{limit} chars)")
        return "\n".join(results) if results else "memory files not found"


def q_cron(q):
    """List cron jobs."""
    if re.search(r"cron|job|schedule|ตาราง|งาน", q, re.IGNORECASE):
        jf = HERMES / "cron" / "jobs.json"
        if jf.exists():
            data = json.loads(jf.read_text())
            jobs = data.get("jobs", data) if isinstance(data, dict) else data
            lines = [f"Total: {len(jobs)} active"]
            for j in jobs[:8]:
                name = j.get("name", "?")[:40]
                sched = j.get("schedule", "?")
                lines.append(f"  • {sched} — {name}")
            return "\n".join(lines)


def q_files(q):
    """File queries (list, count, size)."""
    # Match: "list ไฟล์ X" or "กี่ไฟล์ใน X"
    m = re.search(r"(?:list|นับ|count|กี่ไฟล์|ไฟล์อะไร).*?ใน\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if not m:
        m = re.search(r"list\s+(.+?)(?:\?|$)", q, re.IGNORECASE)
    if m:
        path = m.group(1).strip()
        if not path.startswith("/"):
            path = str(HERMES / path)
        if os.path.isdir(path):
            files = list(os.listdir(path))
            return f"{path}: {len(files)} files — {', '.join(files[:5])}{'...' if len(files) > 5 else ''}"
        elif os.path.isfile(path):
            size = os.path.getsize(path)
            return f"{path}: {size} bytes"


def q_disk(q):
    """Disk usage."""
    if re.search(r"disk|พื้นที่|storage|free space", q, re.IGNORECASE):
        r = subprocess.run(["df", "-h", str(HERMES)], capture_output=True, text=True, timeout=5)
        return r.stdout


def q_git(q):
    """Git status / commits."""
    if re.search(r"git|commit|push", q, re.IGNORECASE):
        r = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5, cwd=HERMES / "notes"
        )
        return f"Recent commits:\n{r.stdout.strip()}"


def q_processes(q):
    """Check processes."""
    if re.search(r"process|ทำงานอะไร|running", q, re.IGNORECASE):
        r = subprocess.run(["pgrep", "-af", "python3|cron|node"], capture_output=True, text=True, timeout=5)
        return r.stdout[:500] if r.stdout else "no python/cron/node processes"


HANDLERS = [q_time, q_date, q_memory, q_cron, q_files, q_disk, q_git, q_processes]


def try_bypass(query: str) -> str | None:
    """Try to answer query without LLM. Return answer or None."""
    for handler in HANDLERS:
        try:
            result = handler(query)
            if result:
                return f"⚡ BYPASS (no LLM):\n{result}"
        except Exception:
            continue
    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 quick_respond.py '<query>'")
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    result = try_bypass(query)
    if result:
        print(result)
        sys.exit(0)
    else:
        print("LLM_REQUIRED")
        sys.exit(2)
