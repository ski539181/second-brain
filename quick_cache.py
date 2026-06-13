#!/usr/bin/env python3
"""
quick_cache.py - Pre-compute common queries (Option 3)

Runs every 5 min via cron. Saves to ~/.hermes/cache/quick-stats.json
Agent reads file instead of running tools.

Token cost: 0 (Python only).
"""
import json
import os
import subprocess
import sqlite3
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
CACHE_FILE = CACHE / "quick-stats.json"


def get_memory():
    out = {}
    for name, limit in [("MEMORY.md", 3000), ("USER.md", 1800)]:
        p = HERMES / "memories" / name
        if p.exists():
            text = p.read_text()
            out[name] = {
                "chars": len(text),
                "limit": limit,
                "pct": round(100 * len(text) / limit, 1),
            }
    return out


def get_disk():
    r = subprocess.run(["df", "-h", str(HERMES)], capture_output=True, text=True, timeout=5)
    return r.stdout.strip().split("\n")[1] if r.stdout else ""


def get_kanban():
    db = HERMES / "kanban.db"
    if not db.exists():
        return {"active": 0, "done": 0}
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        counts = dict(cur.fetchall())
        conn.close()
        return {
            "active": counts.get("ready", 0) + counts.get("in_progress", 0),
            "done": counts.get("done", 0),
        }
    except Exception:
        return {"active": 0, "done": 0}


def get_cron():
    jf = HERMES / "cron" / "jobs.json"
    if not jf.exists():
        return []
    try:
        data = json.loads(jf.read_text())
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        return [{"name": j.get("name", "?"), "schedule": j.get("schedule", "?")}
                for j in jobs]
    except Exception:
        return []


def get_recent_commits(n=5):
    r = subprocess.run(
        ["git", "log", "--oneline", f"-{n}"],
        capture_output=True, text=True, timeout=5, cwd=HERMES / "notes"
    )
    return r.stdout.strip().split("\n") if r.stdout.strip() else []


def get_notes_count():
    notes = HERMES / "notes"
    if notes.exists():
        return len([f for f in notes.rglob("*.md") if "archive" not in str(f)])
    return 0


def get_token_stats():
    """Get today's token usage from token_counter."""
    try:
        r = subprocess.run(
            ["python3", str(HERMES / "scripts" / "token_counter.py"), "stats"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return {"date": "unknown", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0}


def main():
    data = {
        "generated_at": datetime.now().isoformat(),
        "memory": get_memory(),
        "disk": get_disk(),
        "kanban": get_kanban(),
        "cron_jobs": get_cron(),
        "recent_commits": get_recent_commits(5),
        "notes_count": get_notes_count(),
        "tokens_today": get_token_stats(),
    }
    CACHE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✅ Cached {len(data)} fields to {CACHE_FILE}")


if __name__ == "__main__":
    main()
