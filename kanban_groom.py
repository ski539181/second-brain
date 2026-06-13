#!/usr/bin/env python3
"""
kanban_groom.py - Daily kanban maintenance

Automates:
- Archive done tasks > N days old
- Flag stale in_progress tasks (> 7 days no update)
- Detect duplicates (similar titles)
- Generate grooming report
- Dry-run mode for safe testing

Env config:
  KANBAN_ARCHIVE_DAYS=7      (archive done tasks older than N days)
  KANBAN_STALE_DAYS=7        (flag in_progress without update > N days)
  KANBAN_SIMILAR_THRESHOLD=0.7  (Jaccard threshold for duplicate detection)
"""
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
KANBAN_DB = HERMES / "kanban.db"
ARCHIVE_DB = HERMES / "kanban-archive.db"
LOG_FILE = HERMES / "logs" / "kanban-groom.jsonl"

ARCHIVE_DAYS = int(os.environ.get("KANBAN_ARCHIVE_DAYS", "7"))
STALE_DAYS = int(os.environ.get("KANBAN_STALE_DAYS", "7"))
SIMILAR_THRESHOLD = float(os.environ.get("KANBAN_SIMILAR_THRESHOLD", "0.7"))


def jaccard_similarity(s1, s2):
    """Jaccard similarity for duplicate detection (word-based)."""
    words1 = set(re.findall(r"\w+", s1.lower()))
    words2 = set(re.findall(r"\w+", s2.lower()))
    if not words1 or not words2:
        return 0
    return len(words1 & words2) / len(words1 | words2)


def find_duplicates(tasks):
    """Find task pairs with similarity above threshold."""
    dups = []
    titles = [(t.get("task_id", t.get("id", "?")), t.get("title", t.get("name", ""))) for t in tasks]
    for i, (id1, t1) in enumerate(titles):
        for j, (id2, t2) in enumerate(titles):
            if i < j and t1 and t2:
                sim = jaccard_similarity(t1, t2)
                if sim >= SIMILAR_THRESHOLD:
                    dups.append((id1, t2, id2, t1, sim))
    return dups


def main():
    dry_run = "--dry-run" in sys.argv
    if not KANBAN_DB.exists():
        print(f"❌ Kanban DB not found at {KANBAN_DB}")
        return 1

    conn = sqlite3.connect(str(KANBAN_DB))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Discover schema
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r["name"] for r in cur.fetchall()]
    print(f"🧹 Kanban Groom — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Tables: {tables}")

    tasks_table = "tasks" if "tasks" in tables else tables[0] if tables else None
    if not tasks_table:
        print("❌ No tasks table found")
        return 1

    # Get columns
    cur.execute(f"PRAGMA table_info({tasks_table})")
    cols = [r["name"] for r in cur.fetchall()]
    print(f"   Columns: {cols}")

    # Get all tasks
    cur.execute(f"SELECT * FROM {tasks_table}")
    tasks = [dict(r) for r in cur.fetchall()]
    print(f"   Total tasks: {len(tasks)}")

    # Identify actions
    now = datetime.now()
    cutoff = now - timedelta(days=ARCHIVE_DAYS)
    stale_cutoff = now - timedelta(days=STALE_DAYS)

    actions = {
        "archive_done": [],  # (id, title, completed_at)
        "flag_stale": [],    # (id, title, last_update)
        "duplicates": [],    # (id1, t1, id2, t2, sim)
    }

    for t in tasks:
        status = t.get("status", "")
        title = t.get("title", t.get("name", t.get("task_id", "?")))
        tid = t.get("task_id", t.get("id", "?"))

        # Archive done
        if status == "done":
            comp = t.get("completed_at") or t.get("updated_at")
            if comp:
                try:
                    comp_dt = datetime.fromtimestamp(float(comp)) if isinstance(comp, (int, str)) and str(comp).isdigit() else datetime.fromisoformat(str(comp).replace("Z", ""))
                    if comp_dt < cutoff:
                        actions["archive_done"].append((tid, title, comp_dt.isoformat()))
                except Exception:
                    pass

        # Flag stale in_progress
        if status == "in_progress":
            updated = t.get("updated_at") or t.get("created_at")
            if updated:
                try:
                    upd_dt = datetime.fromtimestamp(float(updated)) if isinstance(updated, (int, str)) and str(updated).isdigit() else datetime.fromisoformat(str(updated).replace("Z", ""))
                    if upd_dt < stale_cutoff:
                        actions["flag_stale"].append((tid, title, upd_dt.isoformat()))
                except Exception:
                    pass

    # Duplicates
    actions["duplicates"] = find_duplicates(tasks)

    # Report
    print(f"\n📋 Actions found:")
    print(f"   Archive (done > {ARCHIVE_DAYS}d): {len(actions['archive_done'])}")
    for tid, title, ts in actions["archive_done"][:3]:
        print(f"     • {tid[:10]}: {title[:50]} ({ts})")
    if len(actions["archive_done"]) > 3:
        print(f"     ... and {len(actions['archive_done']) - 3} more")

    print(f"   Stale (in_progress > {STALE_DAYS}d): {len(actions['flag_stale'])}")
    for tid, title, ts in actions["flag_stale"][:3]:
        print(f"     • {tid[:10]}: {title[:50]} ({ts})")

    print(f"   Duplicates (sim ≥ {SIMILAR_THRESHOLD}): {len(actions['duplicates'])}")
    for id1, t1, id2, t2, sim in actions["duplicates"][:3]:
        print(f"     • {id1[:10]} ↔ {id2[:10]} ({sim:.0%}): '{t1[:30]}' vs '{t2[:30]}'")

    if dry_run:
        print("\n[DRY-RUN: no changes made]")
        return 0

    # Apply: archive
    if actions["archive_done"]:
        if not ARCHIVE_DB.exists():
            # Initialize archive DB with same schema
            import shutil
            shutil.copy(KANBAN_DB, ARCHIVE_DB)
        arch_conn = sqlite3.connect(str(ARCHIVE_DB))
        arch_cur = arch_conn.cursor()
        for tid, _, _ in actions["archive_done"]:
            arch_cur.execute(f"INSERT OR IGNORE INTO {tasks_table} SELECT * FROM {tasks_table} WHERE task_id=?", (tid,))
        arch_conn.commit()
        arch_conn.close()
        # Delete from main
        for tid, _, _ in actions["archive_done"]:
            cur.execute(f"DELETE FROM {tasks_table} WHERE task_id=?", (tid,))
        conn.commit()
        print(f"\n✅ Archived {len(actions['archive_done'])} tasks")

    # Log grooming run
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "ts": now.isoformat(),
            "actions": {k: len(v) for k, v in actions.items()},
        }) + "\n")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
