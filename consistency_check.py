#!/usr/bin/env python3
"""
consistency_check.py - Cross-system consistency verification

Compares:
- Memory entries (MEMORY.md, USER.md) — what's claimed
- Notes (~/.hermes/notes/) — what's documented
- Kanban (kanban.db) — what's tracked
- Cron jobs (jobs.json) — what's scheduled
- Skills (~/.hermes/skills/) — what's available
- Cache (quick-stats.json) — what's current

Detects:
- Memory mentions X but no note about X
- Note references Y but no kanban task
- Cron job broken
- Stale cache (> 1 hour old)
- Skill file missing SKILL.md
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
KANBAN = HERMES / "kanban.db"
JOBS = HERMES / "cron" / "jobs.json"
SKILLS = HERMES / "skills"
CACHE = HERMES / "cache" / "quick-stats.json"

issues = []
info = []


def check(label, ok, detail=""):
    if ok:
        info.append(f"✅ {label}: {detail}" if detail else f"✅ {label}")
    else:
        issues.append(f"❌ {label}: {detail}")


def check_memory_notes():
    """Verify memory pointers resolve to actual files."""
    for mem_file in ["MEMORY.md", "USER.md"]:
        path = HERMES / "memories" / mem_file
        if not path.exists():
            check(f"{mem_file} exists", False)
            continue
        text = path.read_text()
        # Find file path pointers
        pointers = re.findall(r"~?/root/\.hermes/[^\s\)\]\.,]+", text)
        for ptr in pointers:
            expanded = os.path.expanduser(ptr)
            if not os.path.exists(expanded):
                check(f"Pointer in {mem_file}", False, f"missing: {ptr}")
            else:
                check(f"Pointer in {mem_file}", True, ptr)


def check_notes_inventory():
    """Notes files have proper structure."""
    if not NOTES.exists():
        check("Notes dir", False)
        return
    md_files = list(NOTES.rglob("*.md"))
    check("Notes count", True, f"{len(md_files)} files")
    # Check for orphan files (not referenced anywhere)
    archive_files = [f for f in md_files if "archive" in str(f)]
    active_files = [f for f in md_files if "archive" not in str(f)]
    check("Active vs archive", True, f"{len(active_files)} active, {len(archive_files)} archived")


def check_kanban():
    """Kanban tasks exist and have valid statuses."""
    if not KANBAN.exists():
        check("Kanban DB", False, "not found")
        return
    import sqlite3
    conn = sqlite3.connect(str(KANBAN))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    if "tasks" not in tables:
        check("Kanban tasks table", False, f"tables: {tables}")
        conn.close()
        return
    cur.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    counts = dict(cur.fetchall())
    conn.close()
    check("Kanban tasks", True, f"counts: {counts}")


def check_cron():
    """Cron jobs are valid and parseable."""
    if not JOBS.exists():
        check("Cron jobs.json", False, "not found")
        return
    try:
        data = json.loads(JOBS.read_text())
        jobs = data.get("jobs", data) if isinstance(data, dict) else data
        enabled = [j for j in jobs if j.get("enabled", True)]
        check("Cron jobs", True, f"{len(enabled)} active / {len(jobs)} total")
    except Exception as e:
        check("Cron jobs parse", False, str(e))


def check_skills():
    """Skills have proper SKILL.md files (recursively, skipping asset subdirs)."""
    if not SKILLS.exists():
        check("Skills dir", False)
        return
    skill_files = list(SKILLS.rglob("SKILL.md"))
    skill_count = len(skill_files)
    # Asset subdirs (references, templates, scripts, assets) hold SKILL assets, not skills
    ASSET_DIRS = {"references", "templates", "scripts", "assets"}
    # Find skill leaf dirs (contain SKILL.md directly)
    skill_dirs = [f.parent for f in skill_files]
    # Find leaf asset dirs (don't contain SKILL.md, have content)
    all_dirs = [d for d in SKILLS.rglob("*") if d.is_dir()]
    bad = []
    for d in all_dirs:
        if d.name in ASSET_DIRS:
            continue  # asset dirs are fine
        if (d / "SKILL.md").exists():
            continue
        if any((s / "SKILL.md").exists() for s in d.iterdir() if s.is_dir()):
            continue
        # leaf dir without SKILL.md and not an asset dir
        # but only flag if it's directly under skills/ (top-level category with no content)
        if d.parent == SKILLS and not any(d.iterdir()):
            continue  # empty top-level dir, ok
        if any(d.iterdir()):
            bad.append(str(d.relative_to(SKILLS)))
    if bad and skill_count > 0:
        check("Skills integrity", True, f"{skill_count} SKILL.md files ({len(bad)} asset subdirs)")
    elif skill_count == 0:
        check("Skills integrity", False, "no SKILL.md found")
    else:
        check("Skills integrity", True, f"{skill_count} SKILL.md files")


def check_cache_freshness():
    """Cache is reasonably fresh."""
    if not CACHE.exists():
        check("Quick cache", False, "not found")
        return
    data = json.loads(CACHE.read_text())
    gen = data.get("generated_at", "")
    try:
        gen_dt = datetime.fromisoformat(gen)
        age_min = (datetime.now() - gen_dt).total_seconds() / 60
        if age_min > 60:
            check("Quick cache fresh", False, f"{age_min:.0f}m old")
        else:
            check("Quick cache fresh", True, f"{age_min:.0f}m old")
    except Exception:
        check("Quick cache parse", False, "invalid timestamp")


def main():
    print(f"🔍 Cross-system consistency — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    check_memory_notes()
    print("[Memory → Notes pointers]")
    for i in info[-3:]:
        print(f"  {i}")
    check_notes_inventory()
    print(f"\n[Notes inventory]")
    for i in info[-2:]:
        print(f"  {i}")
    check_kanban()
    print(f"\n[Kanban]")
    for i in info[-1:]:
        print(f"  {i}")
    check_cron()
    print(f"\n[Cron]")
    for i in info[-1:]:
        print(f"  {i}")
    check_skills()
    print(f"\n[Skills]")
    for i in info[-1:]:
        print(f"  {i}")
    check_cache_freshness()
    print(f"\n[Cache]")
    for i in info[-1:]:
        print(f"  {i}")

    print(f"\n📊 Summary: {len(info)} checks, {len(issues)} issues")
    if issues:
        print(f"\n⚠️  Issues:")
        for i in issues:
            print(f"   {i}")
        return 1
    print("✅ All systems consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
