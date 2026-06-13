#!/usr/bin/env python3
"""
pattern_mining.py - Meta-learning: find patterns in my own activity

Analyzes:
- Cron runs (what fires most, what fails)
- Practice attempts (which challenges repeat)
- Note topics (which areas get most attention)
- Token usage (where cost goes)
- Skill usage (which loaded most)

Output: ~/.hermes/insights/{date}.json + .md
"""
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
LOGS = HERMES / "logs"
NOTES = HERMES / "notes"
INSIGHTS_DIR = HERMES / "insights"
INSIGHTS_DIR.mkdir(exist_ok=True)


def mine_cron_patterns():
    """Analyze cron job patterns."""
    patterns = {"by_hour": Counter(), "by_day": Counter(), "total_jobs": 0}
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.strip().startswith("#") or not line.strip():
                    continue
                # Crude: extract first 5 fields
                parts = line.split()[:5]
                if len(parts) == 5:
                    minute, hour, dom, month, dow = parts
                    # Approximate hour
                    if hour.isdigit():
                        patterns["by_hour"][int(hour)] += 1
                    if dow.isdigit():
                        patterns["by_day"][int(dow)] += 1
                    patterns["total_jobs"] += 1
    except Exception:
        pass
    return patterns


def mine_practice_patterns():
    """What topics/challenges repeat?"""
    pq_file = CACHE / "practice-queue.json"
    if not pq_file.exists():
        return {}
    queue = json.loads(pq_file.read_text())
    challenges = queue.get("challenges", {})
    
    # Group by mastery
    by_mastery = defaultdict(list)
    for pid, data in challenges.items():
        mastery = data.get("mastery", 0)
        by_mastery[mastery].append(int(pid))
    
    # Get topic names
    md = NOTES / "coding-challenges-45.md"
    titles = {}
    if md.exists():
        for m in re.finditer(r"###\s+(\d+)\.\s+(.+?)$", md.read_text(), re.MULTILINE):
            titles[int(m.group(1))] = m.group(2).strip()
    
    weakest = sorted(by_mastery.keys())[:3]
    return {
        "weakest_mastery_levels": weakest,
        "weakest_pids": [by_mastery[m] for m in weakest],
        "weakest_titles": [
            [titles.get(p, f"Q{p}") for p in by_mastery[m][:3]]
            for m in weakest
        ],
    }


def mine_note_patterns():
    """Which note topics get most attention?"""
    if not NOTES.exists():
        return {}
    by_week = defaultdict(Counter)
    by_topic = Counter()
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            week = mtime.strftime("%Y-W%W")
            text = f.read_text().lower()
            # Simple topic detection
            for topic in ["scraper", "memory", "cron", "skill", "token", "telegram", "obsidian", "hermes", "github", "orchestrator"]:
                if topic in text:
                    by_week[week][topic] += 1
                    by_topic[topic] += 1
        except Exception:
            pass
    return {
        "by_topic": dict(by_topic.most_common(10)),
        "recent_weeks": {k: dict(v) for k, v in list(by_week.items())[-4:]},
    }


def mine_token_patterns():
    """Where does token cost go?"""
    log = LOGS / "tokens.jsonl"
    if not log.exists():
        return {"note": "no log yet"}
    by_day = defaultdict(int)
    by_dir = Counter()
    for line in log.read_text().splitlines():
        try:
            e = json.loads(line)
            date = e.get("date", "?")
            by_day[date] += e.get("input", 0) + e.get("output", 0)
            by_dir[e.get("direction", "?")] += e.get("input", 0) + e.get("output", 0)
        except Exception:
            pass
    return {
        "tracked_days": len(by_day),
        "total_tokens": sum(by_day.values()),
        "by_day": dict(sorted(by_day.items())[-7:]),
        "by_direction": dict(by_dir.most_common()),
    }


def mine_skill_patterns():
    """Which skills are loaded most?"""
    # Check the system logs if available
    skills_dir = HERMES / "skills"
    if not skills_dir.exists():
        return {}
    return {
        "total": len(list(skills_dir.rglob("SKILL.md"))),
        "by_category": dict(Counter(
            p.parent.name for p in skills_dir.rglob("SKILL.md")
        ).most_common(5)),
    }


def synthesize_insights(cron, practice, notes, tokens, skills):
    """Generate human-readable insights from all patterns."""
    insights = []
    
    # Cron insights
    if cron.get("total_jobs", 0) > 0:
        peak_hour = max(cron["by_hour"].items(), key=lambda x: x[1]) if cron["by_hour"] else None
        if peak_hour:
            insights.append(f"⏰ Peak cron hour: **{peak_hour[0]:02d}:00** ({peak_hour[1]} jobs)")
    
    # Practice insights
    if practice.get("weakest_pids"):
        weakest = practice["weakest_pids"][0] if practice["weakest_pids"] else []
        if weakest:
            titles = practice.get("weakest_titles", [[]])[0]
            if titles:
                insights.append(f"🎯 Weakest skill: **{titles[0]}** (mastery ~0%)")
                insights.append(f"   → Run `python3 ~/.hermes/scripts/weakest_focus.py` for targeted practice")
    
    # Note insights
    if notes.get("by_topic"):
        top_topic = list(notes["by_topic"].items())[0]
        insights.append(f"📝 Most-edited topic: **{top_topic[0]}** ({top_topic[1]} edits)")
    
    # Token insights
    if tokens.get("tracked_days", 0) > 0:
        avg = tokens.get("total_tokens", 0) / max(1, tokens["tracked_days"])
        insights.append(f"💰 Avg tokens/day: **{avg:,.0f}**")
    
    # Skill insights
    if skills.get("total", 0) > 0:
        insights.append(f"🧠 Skills available: **{skills['total']}**")
    
    return insights


def main():
    print(f"🔍 Pattern Mining — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    cron = mine_cron_patterns()
    practice = mine_practice_patterns()
    notes = mine_note_patterns()
    tokens = mine_token_patterns()
    skills = mine_skill_patterns()
    
    print(f"⏰ Cron: {cron.get('total_jobs', 0)} jobs")
    print(f"🎯 Practice: {len(practice.get('weakest_pids', [[]])[0])} weakest challenges")
    print(f"📝 Notes: {len(notes.get('by_topic', {}))} topics tracked")
    print(f"💰 Tokens: {tokens.get('tracked_days', 0)} days tracked")
    print(f"🧠 Skills: {skills.get('total', 0)} available")
    
    insights = synthesize_insights(cron, practice, notes, tokens, skills)
    
    # Save
    out_json = INSIGHTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    out_json.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "cron": cron,
        "practice": practice,
        "notes": notes,
        "tokens": tokens,
        "skills": skills,
    }, indent=2, default=str))
    
    out_md = INSIGHTS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    md = f"# 🔍 Pattern Mining — {datetime.now().strftime('%Y-%m-%d')}\n\n"
    md += "## 💡 Key insights\n\n"
    for i in insights:
        md += f"- {i}\n"
    md += "\n## 📊 Raw data\n\n"
    md += f"- Cron jobs: {cron.get('total_jobs', 0)}\n"
    md += f"- Practice challenges: {len(practice.get('weakest_pids', [[]])[0])} weak\n"
    md += f"- Note topics: {len(notes.get('by_topic', {}))} tracked\n"
    md += f"- Token days: {tokens.get('tracked_days', 0)}\n"
    md += f"- Skills: {skills.get('total', 0)}\n"
    out_md.write_text(md)
    
    print(f"\n📄 Saved: {out_json}")
    print(f"📄 Saved: {out_md}")
    print(f"\n💡 {len(insights)} insights generated")
    return 0


if __name__ == "__main__":
    exit(main())
