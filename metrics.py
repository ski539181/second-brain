#!/usr/bin/env python3
"""
metrics.py - Comprehensive learning metrics dashboard

Aggregates:
- Practice queue (mastery, attempts, pass rate)
- Reflection journal (entries over time)
- Token usage (daily trend)
- Memory/notes/cron health
- Knowledge graph (notes, links, orphans)

Output: JSON + readable text

Token cost: 0 (Python only)
"""
import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
NOTES = HERMES / "notes"
SCRIPTS = HERMES / "scripts"
SKILLS = HERMES / "skills"
JOURNAL = HERMES / "journal"


def load_json(path, default=None):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default if default is not None else {}


def practice_metrics():
    state = load_json(CACHE / "practice-queue.json", {"challenges": {}})
    cs = state["challenges"]
    if not cs:
        return {"total": 0, "avg_mastery": 0, "by_status": {}}
    total = len(cs)
    by_status = {}
    for c in cs.values():
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
    avg_mastery = sum(c["mastery"] for c in cs.values()) / total
    total_attempts = sum(c["attempts"] for c in cs.values())
    total_passes = sum(c["passes"] for c in cs.values())
    return {
        "total": total,
        "avg_mastery": round(avg_mastery, 1),
        "by_status": by_status,
        "attempts": total_attempts,
        "passes": total_passes,
        "pass_rate": round(total_passes / total_attempts * 100, 1) if total_attempts else 0,
    }


def journal_metrics():
    if not JOURNAL.exists():
        return {"total": 0, "this_week": 0, "last": None}
    files = list(JOURNAL.glob("*.md"))
    week_ago = datetime.now() - timedelta(days=7)
    this_week = sum(1 for f in files if datetime.fromtimestamp(f.stat().st_mtime) > week_ago)
    last = max(files, key=lambda f: f.stat().st_mtime) if files else None
    return {
        "total": len(files),
        "this_week": this_week,
        "last": last.name if last else None,
    }


def token_metrics():
    log = HERMES / "logs" / "tokens.jsonl"
    if not log.exists():
        return {"tracked_days": 0, "total_today": 0}
    by_day = {}
    for line in log.read_text().splitlines():
        try:
            entry = json.loads(line)
            d = entry.get("date", "unknown")
            by_day[d] = by_day.get(d, 0) + entry.get("input", 0) + entry.get("output", 0)
        except Exception:
            pass
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "tracked_days": len(by_day),
        "total_today": by_day.get(today, 0),
        "week_total": sum(v for d, v in by_day.items() if d >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")),
    }


def notes_metrics():
    if not NOTES.exists():
        return {"total": 0, "with_wikilinks": 0, "orphans": 0}
    files = [f for f in NOTES.rglob("*.md") if "archive" not in str(f)]
    with_links = 0
    all_links = set()
    all_titles = set()
    for f in files:
        text = f.read_text()
        links = re.findall(r"\[\[([^\]]+)\]\]", text)
        if links:
            with_links += 1
        for l in links:
            all_links.add(l)
        # Track titles (first H1)
        m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
        if m:
            all_titles.add(m.group(1).strip())
    orphans = all_links - all_titles
    return {
        "total": len(files),
        "with_wikilinks": with_links,
        "orphan_links": len(orphans),
        "unique_titles": len(all_titles),
    }


def cron_metrics():
    jobs_file = HERMES / "cron" / "jobs.json"
    if not jobs_file.exists():
        return {"total": 0, "active": 0}
    try:
        data = json.loads(jobs_file.read_text())
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        if isinstance(jobs, list):
            active = sum(1 for j in jobs if j.get("enabled", True) and not j.get("paused", False))
            return {"total": len(jobs), "active": active}
    except Exception:
        pass
    return {"total": 0, "active": 0}


def skills_metrics():
    if not SKILLS.exists():
        return {"total": 0}
    skills = [f for f in SKILLS.rglob("SKILL.md")]
    return {"total": len(skills)}


def scripts_metrics():
    if not SCRIPTS.exists():
        return {"total": 0, "total_kb": 0}
    py_files = list(SCRIPTS.glob("*.py"))
    total_bytes = sum(f.stat().st_size for f in py_files)
    return {"total": len(py_files), "total_kb": round(total_bytes / 1024, 1)}


def main():
    metrics = {
        "generated_at": datetime.now().isoformat(),
        "practice": practice_metrics(),
        "journal": journal_metrics(),
        "tokens": token_metrics(),
        "notes": notes_metrics(),
        "cron": cron_metrics(),
        "skills": skills_metrics(),
        "scripts": scripts_metrics(),
    }

    # Save
    out = CACHE / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2))

    # Print pretty
    print(f"📊 Learning Metrics Dashboard — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    print(f"🎯 Practice queue:")
    p = metrics["practice"]
    print(f"   Challenges: {p['total']} | Avg mastery: {p['avg_mastery']}% | Pass rate: {p.get('pass_rate', 0)}%")
    print(f"   By status: {p['by_status']}")
    print()
    print(f"📔 Reflection journal:")
    j = metrics["journal"]
    print(f"   Total: {j['total']} | This week: {j['this_week']} | Last: {j['last']}")
    print()
    print(f"💰 Tokens:")
    t = metrics["tokens"]
    print(f"   Tracked days: {t['tracked_days']} | Today: {t['total_today']} | Week: {t['week_total']}")
    print()
    print(f"📝 Notes:")
    n = metrics["notes"]
    print(f"   Total: {n['total']} | With wikilinks: {n['with_wikilinks']} | Orphan links: {n['orphan_links']}")
    print()
    print(f"⏰ Cron: {metrics['cron']['active']}/{metrics['cron']['total']} active")
    print(f"🧠 Skills: {metrics['skills']['total']}")
    print(f"🛠️ Scripts: {metrics['scripts']['total']} ({metrics['scripts']['total_kb']} KB)")

    # Improvement score (composite)
    score = 0
    score += min(50, p['avg_mastery'])  # up to 50 points
    score += min(20, j['this_week'] * 5)  # up to 20 points
    score += min(15, n['with_wikilinks'])  # up to 15 points
    score += min(15, metrics['skills']['total'])  # up to 15 points
    print(f"\n🌟 Overall learning score: {score:.0f}/100")
    print(f"\n📄 Saved: {out}")
    return 0


if __name__ == "__main__":
    exit(main())
