#!/usr/bin/env python3
"""
daily_summary.py - Generate daily activity summary

Runs 20:00 TH daily. Reports:
- What got done (git commits)
- Active cron jobs
- Memory/Negotiation state
- Kanban status
- Pending alerts

Output: ~/.hermes/notes/daily-summaries/YYYY-MM-DD.md
"""
import json
import subprocess
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
KANBAN = HERMES / "kanban.db"
NOW = datetime.now()
SUMMARIES = NOTES / "daily-summaries"


def git_commits_today():
    r = subprocess.run(
        ["git", "log", "--since=24 hours ago", "--oneline"],
        capture_output=True, text=True, timeout=10, cwd=NOTES
    )
    return r.stdout.strip().split("\n") if r.stdout.strip() else []


def memory_state():
    out = {}
    for name, limit in [("MEMORY.md", 3000), ("USER.md", 1800)]:
        p = HERMES / "memories" / name
        if p.exists():
            size = p.stat().st_size
            out[name] = f"{size}/{limit} ({100*size/limit:.0f}%)"
    return out


def kanban_state():
    if not KANBAN.exists():
        return {"active": 0, "done_today": 0}
    try:
        conn = sqlite3.connect(str(KANBAN))
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        counts = dict(cur.fetchall())
        conn.close()
        return {
            "active": counts.get("ready", 0) + counts.get("in_progress", 0),
            "done_today": counts.get("done", 0),
        }
    except Exception:
        return {"active": 0, "done_today": 0}


def cron_jobs():
    jf = HERMES / "cron" / "jobs.json"
    if not jf.exists():
        return []
    try:
        data = json.loads(jf.read_text())
        # jobs.json is {"jobs": [...], "updated_at": "..."}; tolerate bare list too
        if isinstance(data, list):
            return data
        return data.get("jobs", [])
    except Exception:
        return []


def main():
    SUMMARIES.mkdir(parents=True, exist_ok=True)
    today = NOW.strftime("%Y-%m-%d")
    output = SUMMARIES / f"{today}.md"

    commits = git_commits_today()
    mem = memory_state()
    kan = kanban_state()
    crons = cron_jobs()

    lines = [
        f"# Daily Summary — {today}",
        "",
        f"Generated: {NOW.strftime('%H:%M %Z')}",
        "",
        "## 📦 Commits (24h)",
        f"Total: **{len(commits)}** commits",
        "",
    ]
    for c in commits[:10]:
        lines.append(f"- {c}")
    if not commits:
        lines.append("- (none)")

    lines += [
        "",
        "## 🧠 Memory",
        "",
    ]
    for k, v in mem.items():
        lines.append(f"- {k}: {v}")

    lines += [
        "",
        "## 📋 Kanban",
        f"- Active: {kan['active']}",
        f"- Done (total): {kan['done_today']}",
        "",
        "## ⏰ Active Cron Jobs",
        f"Total: {len(crons)}",
        "",
    ]
    for j in crons[:10]:
        name = j.get("name", "?").replace("\n", " ").strip()
        sched = j.get("schedule_display") or j.get("schedule", "?")
        lines.append(f"- `{sched}` — {name}")

    output.write_text("\n".join(lines))
    print(f"✅ Summary written: {output}")
    print(f"   Commits: {len(commits)}, Cron: {len(crons)}, Kanban active: {kan['active']}")


if __name__ == "__main__":
    main()
