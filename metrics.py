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


def bar(pct, width=20, goal=None, color=False):
    """Progress bar with optional goal marker.

    Args:
        pct: current percentage (0-100)
        width: total bar width
        goal: target percentage to mark (e.g., 50)
        color: ANSI colors (works in terminal, ignored in Telegram)
    """
    pct = max(0, min(100, pct))
    filled = int(width * pct / 100)
    bar_str = "█" * filled + "░" * (width - filled)

    # Insert goal marker
    if goal is not None and 0 < goal < 100:
        goal_pos = int(width * goal / 100)
        if goal_pos >= filled:
            bar_str = bar_str[:goal_pos] + "│" + bar_str[goal_pos+1:]
        else:
            # Goal already passed
            bar_str = bar_str[:goal_pos] + "┤" + bar_str[goal_pos+1:]

    if color:
        if pct >= goal if goal else pct >= 80:
            return f"\033[92m{bar_str}\033[0m"  # green
        elif pct >= (goal * 0.6 if goal else 50):
            return f"\033[93m{bar_str}\033[0m"  # yellow
        else:
            return f"\033[91m{bar_str}\033[0m"  # red

    return bar_str


def status_emoji(pct, goal=50):
    """Emoji based on progress toward goal."""
    if pct >= goal:
        return "🟢"
    elif pct >= goal * 0.6:
        return "🟡"
    else:
        return "🔴"


def print_pretty(metrics):
    """Pretty Thai output."""
    p = metrics["practice"]
    j = metrics["journal"]
    t = metrics["tokens"]
    n = metrics["notes"]
    c = metrics["cron"]
    sk = metrics["skills"]
    sc = metrics["scripts"]
    cost = t['week_total'] * 0.00021 / 1000  # for token section
    print(f"📊 ระบบเรียนรู้ของ Hermes — รายงานประจำวัน\n")
    print("═" * 50)
    print("\n🎯 ทักษะ (Practice)")
    print(f"   ฝึกแล้ว:  {p['total']}/45 ข้อ")
    mastery = p['avg_mastery']
    e = status_emoji(mastery, 50)
    print(f"   {e} ความเชี่ยวชาญ: {mastery:>5.1f}% {bar(mastery, goal=50)}  ← เป้า 50%")
    pr = p.get('pass_rate', 0)
    e2 = status_emoji(pr, 70)
    print(f"   {e2} ทำถูก:  {pr:>5.1f}% {bar(pr, goal=70)}  ← เป้า 70%")
    print(f"   ครั้งที่ลอง: {p['attempts']} | ทำผ่าน: {p['passes']}")
    explain = {
        "new": "ยังไม่เคยลอง",
        "learning": "กำลังเรียนรู้ (ฝึกบ่อย)",
        "reviewing": "ทบทวน (ทุก 3 วัน)",
        "mastered": "เชี่ยวชาญแล้ว (ทุก 14 วัน)",
    }
    status_parts = [f"{explain.get(s, s)} {n}" for s, n in p['by_status'].items()]
    print(f"   สถานะ: {', '.join(status_parts)}")

    print("\n📔 บันทึกการเรียนรู้ (Journal)")
    j_emoji = status_emoji(j['total'], 7)
    print(f"   {j_emoji} บันทึกทั้งหมด: {j['total']} รายการ {bar(j['total']*14.28, goal=100)}  ← เป้า 7")
    print(f"   สัปดาห์นี้: {j['this_week']} รายการ")
    print(f"   ล่าสุด: {j['last'] or 'ยังไม่มี'}")

    print("\n💰 การใช้ tokens")
    # Cost as % of weekly budget (e.g., $5 = 100%)
    weekly_budget_usd = 5.0
    cost_pct = min(100, (cost / weekly_budget_usd) * 100) if cost > 0 else 0
    cost_emoji = "🟢" if cost < 0.5 else "🟡" if cost < 2 else "🔴"
    print(f"   {cost_emoji} บันทึกไว้: {t['tracked_days']} วัน")
    print(f"   📊 วันนี้: {t['total_today']:,} tokens")
    print(f"   📊 สัปดาห์นี้: {t['week_total']:,} tokens")
    print(f"   💵 ค่าใช้จ่าย: ${cost:.4f} {bar(cost_pct, goal=20)}  ← เป้า <$1/สัปดาห์")

    print("\n📝 คลังความรู้ (Notes)")
    print(f"   ไฟล์ทั้งหมด: {n['total']} ไฟล์")
    linked = n['with_wikilinks']
    linked_pct = linked / n['total'] * 100 if n['total'] else 0
    e3 = status_emoji(linked_pct, 30)
    print(f"   {e3} เชื่อมโยงกัน: {linked}/{n['total']} ({linked_pct:.0f}%) {bar(linked_pct, goal=30)}  ← เป้า 30%")
    print(f"   ลิงก์เดียวดาย: {n['orphan_links']} ลิงก์")

    print("\n⚙️  ระบบอัตโนมัติ")
    cron_pct = c['active'] / c['total'] * 100 if c['total'] else 0
    e4 = status_emoji(cron_pct, 90)
    print(f"   {e4} Cron jobs: {c['active']}/{c['total']} ทำงาน {bar(cron_pct, goal=100)}")
    print(f"   Skills: {sk['total']} ตัว")
    print(f"   Scripts: {sc['total']} ตัว ({sc['total_kb']} KB)")

    print("\n" + "═" * 50)
    score = 0
    score += min(50, p['avg_mastery'])
    score += min(20, j['this_week'] * 5)
    score += min(15, n['with_wikilinks'])
    score += min(15, sk['total'])
    s_emoji = status_emoji(score, 50)
    print(f"\n{s_emoji} คะแนนรวม: {score:.1f}/100 {bar(score, goal=50)}  ← เป้า 50")
    print(f"   {bar(score, goal=50)} ← ตำแหน่งปัจจุบัน (เส้น │ = เป้า)")

    print("\n📌 แนะนำทำต่อ:")
    recs = []
    if mastery < 50:
        recs.append(f"1. ฝึก challenges ที่ยังไม่ผ่าน (mastery {mastery:.0f}% → เป้า 50%)")
    if linked < n['total'] * 0.3:
        recs.append(f"2. เพิ่ม [[wikilinks]] ใน notes ({linked} → เป้า 30%)")
    if j['total'] < 7:
        recs.append("3. เขียน journal ให้ครบ 7 วัน")
    if not recs:
        recs.append("✓ ทุกอย่างในเกณฑ์ดี — ทำต่อเพื่อรักษาระดับ")
    for r in recs:
        print(f"   {r}")
    print()


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

    out = CACHE / "metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(metrics, indent=2))

    # Compute cost before print
    cost = metrics["tokens"]["week_total"] * 0.00021 / 1000

    print_pretty(metrics)
    print(f"📄 Saved: {out}")
    return 0


if __name__ == "__main__":
    exit(main())
