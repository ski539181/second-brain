#!/usr/bin/env python3
"""
reflection.py - Auto-generate reflection journal entries

Reads recent activity (logs, cron output, notes) and writes a journal entry.

Format:
  Date | What I did | What worked | What failed | Lessons | Next actions

Token cost: 0 (Python only)
"""
import os
import sys
import re
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
JOURNAL_DIR = HERMES / "journal"
CACHE = HERMES / "cache"

# Optional LLM support — generate richer insights
try:
    sys.path.insert(0, str(HERMES / "scripts"))
    from llm_helper import llm_call
    HAS_LLM = True
except Exception:
    HAS_LLM = False


def ensure_dir():
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)


def get_recent_activity():
    """Scan recent files and logs for activity."""
    activity = {
        "notes_created": [],
        "scripts_created": [],
        "skills_created": [],
        "commits": [],
    }
    # Recent files in notes (last 7 days)
    notes = HERMES / "notes"
    if notes.exists():
        for f in notes.rglob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > datetime.now() - timedelta(days=7):
                    activity["notes_created"].append(f.name)
            except Exception:
                pass
    # Recent scripts
    scripts = HERMES / "scripts"
    if scripts.exists():
        for f in scripts.iterdir():
            if f.suffix == ".py":
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime > datetime.now() - timedelta(days=7):
                        activity["scripts_created"].append(f.name)
                except Exception:
                    pass
    # Recent skills
    skills = HERMES / "skills"
    if skills.exists():
        for f in skills.rglob("SKILL.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > datetime.now() - timedelta(days=7):
                    activity["skills_created"].append(str(f.relative_to(skills)))
            except Exception:
                pass
    # Recent commits
    try:
        r = subprocess.run(
            ["git", "-C", str(notes), "log", "--oneline", "-10"],
            capture_output=True, text=True, timeout=10
        )
        activity["commits"] = r.stdout.strip().split("\n") if r.stdout.strip() else []
    except Exception:
        pass
    return activity


def load_metrics():
    """Read quick-stats cache for context."""
    cache_file = CACHE / "quick-stats.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    return {}


def get_token_summary():
    """Read today's token usage."""
    log = HERMES / "logs" / "tokens.jsonl"
    if not log.exists():
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    total_in = total_out = 0
    for line in log.read_text().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("date") == today:
                total_in += entry.get("input", 0)
                total_out += entry.get("output", 0)
        except Exception:
            pass
    return {"input": total_in, "output": total_out}


def get_health_summary():
    """Read latest healthcheck output if exists."""
    health = CACHE / "healthcheck.json"
    if health.exists():
        return json.loads(health.read_text())
    return {}


def reflect():
    """Generate a reflection entry."""
    today = datetime.now().strftime("%Y-%m-%d")
    activity = get_recent_activity()
    metrics = load_metrics()
    tokens = get_token_summary()
    health = get_health_summary()

    # Build reflection
    entry = f"""# Reflection: {today}

## 📊 What I did (last 7 days)
- Notes: {len(activity['notes_created'])} created
- Scripts: {len(activity['scripts_created'])} created
- Skills: {len(activity['skills_created'])} created
- Commits: {len(activity['commits'])} recent

## 💪 What worked
"""
    worked = []
    if activity["notes_created"]:
        worked.append(f"Documented {len(activity['notes_created'])} notes")
    if activity["scripts_created"]:
        worked.append(f"Built {len(activity['scripts_created'])} automation scripts")
    if metrics.get("tokens_today", {}).get("total", 0) > 0:
        worked.append(f"Tracked {metrics['tokens_today']['total']} tokens today")
    if not worked:
        worked.append("No major activity in 7 days")
    for w in worked:
        entry += f"- {w}\n"

    entry += "\n## ⚠️ What didn't work / risks\n"
    failed = []
    # Check memory usage
    mem = metrics.get("memory", {})
    if isinstance(mem, dict):
        if mem.get("percent", 0) > 90:
            failed.append(f"Memory near limit ({mem.get('percent')}%)")
    # Check disk
    disk = metrics.get("disk", {})
    if isinstance(disk, dict) and disk.get("percent", 0) > 80:
        failed.append(f"Disk high ({disk.get('percent')}%)")
    if not failed:
        failed.append("No major failures detected")
    for f in failed:
        entry += f"- {f}\n"

    entry += "\n## 🎓 Lessons learned\n"
    lessons = []
    # Auto-derive from activity
    if len(activity["scripts_created"]) >= 3:
        lessons.append("Multiple scripts in 7 days = high velocity, watch for technical debt")
    if len(activity["notes_created"]) >= 5:
        lessons.append("Note-taking is high — review for cross-references and gaps")
    if tokens and tokens.get("input", 0) > 100000:
        lessons.append(f"High input tokens ({tokens['input']}) — look for context reduction")
    if not lessons:
        lessons.append("Steady state — no new lessons from data")
    for l in lessons:
        entry += f"- {l}\n"

    entry += "\n## 🎯 Next actions\n"
    actions = []
    cron_jobs = metrics.get("cron_jobs", [])
    if isinstance(cron_jobs, list):
        active_count = sum(1 for j in cron_jobs if j.get("enabled", True))
    else:
        active_count = cron_jobs.get("active", 0) if isinstance(cron_jobs, dict) else 0
    if active_count < 15:
        actions.append("Add more automation crons")
    if mem.get("percent", 0) > 70 if isinstance(mem, dict) else False:
        actions.append("Compress memory before limit")
    if not actions:
        actions.append("Continue current pace, review weekly")
    for a in actions:
        entry += f"- [ ] {a}\n"

    entry += f"\n## 📈 Metrics snapshot\n"
    if tokens:
        entry += f"- Tokens today: in={tokens['input']}, out={tokens['output']}\n"
    if mem:
        entry += f"- Memory: {mem.get('used', 0)}/{mem.get('limit', 0)} chars ({mem.get('percent', 0)}%)\n"
    if metrics.get("cron_jobs"):
        if isinstance(metrics["cron_jobs"], list):
            active = sum(1 for j in metrics["cron_jobs"] if j.get("enabled", True))
            entry += f"- Cron jobs: {active} active\n"
        elif isinstance(metrics["cron_jobs"], dict):
            entry += f"- Cron jobs: {metrics['cron_jobs'].get('active', '?')} active\n"
    if metrics.get("kanban"):
        entry += f"- Kanban: {metrics['kanban'].get('done', 0)} done, {metrics['kanban'].get('ready', 0)} ready\n"

    # LLM insight — only if --llm flag and LLM available
    import sys
    if HAS_LLM and "--llm" in sys.argv:
        insight = generate_llm_insight(activity, metrics)
        if insight:
            entry += f"\n## 🤖 LLM Insight\n\n{insight}\n"

    entry += f"\n---\n*Generated by reflection.py at {datetime.now().isoformat()}*\n"
    return entry


def generate_llm_insight(activity, metrics):
    """Generate deeper reflection via LLM (~$0.0001)."""
    prompt = f"""Analyze this day's activity and provide 2-3 insights:

- Notes modified: {len(activity.get('notes', []))}
- Cron runs: {len(activity.get('cron_outputs', []))}
- Scripts executed: {len(activity.get('scripts_run', []))}
- Recent notes topics: {[n.get('title', '?')[:30] for n in activity.get('notes', [])[:5]]}

What went well? What pattern emerges? 1 specific improvement for tomorrow.
Be concise, Thai/English mix, max 100 words."""
    return llm_call(prompt, max_tokens=200)


def main():
    ensure_dir()
    today = datetime.now().strftime("%Y-%m-%d")
    out_file = JOURNAL_DIR / f"{today}.md"

    # If already exists today, append; else create
    entry = reflect()
    if out_file.exists():
        out_file.write_text(out_file.read_text() + "\n\n" + "=" * 60 + "\n\n" + entry)
        print(f"📝 Appended to: {out_file}")
    else:
        out_file.write_text(entry)
        print(f"📝 Created: {out_file}")
    return 0


if __name__ == "__main__":
    exit(main())
