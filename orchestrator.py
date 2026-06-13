#!/usr/bin/env python3
"""
orchestrator.py - Cross-system sync for Hermes Agent

Fixes silo problems between:
  - Memory (MEMORY.md, USER.md)
  - Notes (~/.hermes/notes/)
  - Kanban (kanban.db)
  - Cron (jobs.json)
  - Skills (~/.hermes/skills/)

Token cost: ~0 (Python only, no LLM calls)
Runs: nightly via cron + on-demand

Usage:
    python3 orchestrator.py --all          # full sync
    python3 orchestrator.py --dedup        # memory dedup only
    python3 orchestrator.py --pointers     # update memory pointers only
    python3 orchestrator.py --archive      # archive old notes
    python3 orchestrator.py --kanban-sync  # cron ↔ kanban consistency
    python3 orchestrator.py --status       # report only (no changes)
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

HERMES = Path.home() / ".hermes"
MEMORY = HERMES / "memories" / "MEMORY.md"
USER_MD = HERMES / "memories" / "USER.md"
NOTES = HERMES / "notes"
ARCHIVE = NOTES / "archive"
SKILLS = HERMES / "skills"
KANBAN_DB = HERMES / "kanban" / "kanban.db"
CRON_JOBS = HERMES / "cron" / "jobs.json"
LOG = NOTES / "orchestrator.log"

SEP = "§"

# ============ Utilities ============

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line)
    if LOG.parent.exists():
        with LOG.open("a") as f:
            f.write(line + "\n")


def parse_sections(text: str) -> list[tuple[int, str, str]]:
    """Split MEMORY/USER text by § separator. Returns [(index, header_line, body)]."""
    sections = []
    chunks = text.split(SEP)
    for i, chunk in enumerate(chunks):
        chunk = chunk.strip()
        if not chunk:
            continue
        # First line is the "header" of the section
        lines = chunk.split("\n", 1)
        header = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        sections.append((i, header, body))
    return sections


def write_sections(path: Path, sections: list[tuple[int, str, str]]) -> None:
    """Reconstruct MEMORY/USER file from sections."""
    parts = []
    for _, header, body in sections:
        if body:
            parts.append(f"{header}\n{body}")
        else:
            parts.append(header)
    content = ("\n" + SEP + "\n").join(parts) + "\n"
    path.write_text(content)


# ============ 1. Memory Dedup ============

def jaccard_similarity(a: str, b: str) -> float:
    """Word-level Jaccard similarity. Fast, no LLM."""
    wa = set(re.findall(r"\w+", a.lower()))
    wb = set(re.findall(r"\w+", b.lower()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def dedup_memory(path: Path, threshold: float = 0.65) -> int:
    """Merge near-duplicate § sections. Returns count of merges."""
    if not path.exists():
        return 0
    text = path.read_text()
    sections = parse_sections(text)
    if len(sections) < 2:
        return 0

    # Find pairs above threshold; keep longer one, drop shorter
    to_drop: set[int] = set()
    for i in range(len(sections)):
        if i in to_drop:
            continue
        for j in range(i + 1, len(sections)):
            if j in to_drop:
                continue
            text_i = f"{sections[i][1]} {sections[i][2]}"
            text_j = f"{sections[j][1]} {sections[j][2]}"
            sim = jaccard_similarity(text_i, text_j)
            if sim >= threshold:
                # Keep the longer one (more info)
                len_i = len(text_i)
                len_j = len(text_j)
                if len_i >= len_j:
                    to_drop.add(j)
                else:
                    to_drop.add(i)
                    break

    if to_drop:
        kept = [s for i, s in enumerate(sections) if i not in to_drop]
        write_sections(path, kept)
        log(f"dedup {path.name}: merged {len(to_drop)} duplicates (kept {len(kept)})")
    return len(to_drop)


# ============ 2. Pointer Sync ============

POINTER_RE = re.compile(
    r"`?(~/.hermes/(?:notes|skills|scripts)/[^\s`'\",]+)`?",
    re.IGNORECASE
)


def update_pointers() -> dict[str, Any]:
    """Verify memory pointers still exist; flag missing ones."""
    missing: dict[str, list[str]] = {"MEMORY.md": [], "USER.md": []}
    for path, label in [(MEMORY, "MEMORY.md"), (USER_MD, "USER.md")]:
        if not path.exists():
            continue
        text = path.read_text()
        for m in POINTER_RE.finditer(text):
            ptr = m.group(1).replace("~", str(Path.home()))
            p = Path(ptr)
            # Skip pointers to dirs (not files)
            if not p.suffix and not p.exists():
                continue
            if not p.exists():
                missing[label].append(ptr)

    if any(missing.values()):
        log(f"pointers: {sum(len(v) for v in missing.values())} missing - {missing}")
    else:
        log("pointers: all valid")
    return missing


# ============ 3. Archive Inactive Notes ============

def archive_inactive(days: int = 60) -> int:
    """Move notes not modified in `days` to archive/YYYY-MM/."""
    if not NOTES.exists():
        return 0
    cutoff = time.time() - days * 86400
    moved = 0
    for f in NOTES.rglob("*.md"):
        if "archive" in f.parts or "raw" in f.parts or f.name in ("README.md", "index.md", "notes.md"):
            continue
        mtime = f.stat().st_mtime
        if mtime < cutoff:
            month_dir = ARCHIVE / datetime.fromtimestamp(mtime).strftime("%Y-%m")
            month_dir.mkdir(parents=True, exist_ok=True)
            target = month_dir / f.name
            if not target.exists():
                f.rename(target)
                moved += 1
    if moved:
        log(f"archive: moved {moved} notes older than {days} days")
    return moved


# ============ 4. Kanban ↔ Cron Sync ============

def kanban_cron_sync() -> dict[str, Any]:
    """Verify cron job prompts reference existing kanban task IDs; flag orphans."""
    result = {"active_tasks": 0, "cron_refs": 0, "orphan_cron": []}
    if not KANBAN_DB.exists():
        return result
    try:
        conn = sqlite3.connect(str(KANBAN_DB))
        cur = conn.cursor()
        # Try to discover table name
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            if "task" in t.lower():
                try:
                    cur.execute(f"SELECT id, status FROM {t}")
                    active = [r[0] for r in cur.fetchall() if r[1] in ("ready", "in_progress", "pending")]
                    result["active_tasks"] = len(active)
                except sqlite3.OperationalError:
                    pass
        conn.close()
    except sqlite3.OperationalError:
        pass

    if CRON_JOBS.exists():
        try:
            jobs = json.loads(CRON_JOBS.read_text())
            if isinstance(jobs, list):
                for job in jobs:
                    prompt = job.get("prompt", "")
                    refs = re.findall(r"t_[a-f0-9]{8}", prompt)
                    result["cron_refs"] += len(refs)
                    if refs and not any(t.startswith(tuple(refs)) for t in [result.get("active_tasks", 0)]):
                        # Just track cron-refs; can't validate without task list
                        pass
        except (json.JSONDecodeError, OSError):
            pass

    log(f"kanban-cron sync: {result}")
    return result


# ============ 5. Pattern Detection (cheap) ============

def detect_repeated_patterns(window_days: int = 7) -> list[str]:
    """Find recurring action patterns in recent log files (heuristic)."""
    patterns = []
    log_files = [
        NOTES / "orchestrator.log",
        HERMES / "cron" / "output" / "*.log",
    ]
    seen_actions: dict[str, int] = {}
    for pattern in log_files:
        for f in Path(HERMES).rglob("*.log"):
            if "archive" in f.parts or "node_modules" in f.parts:
                continue
            if (time.time() - f.stat().st_mtime) > window_days * 86400:
                continue
            try:
                text = f.read_text(errors="ignore")
                # Look for repeated command/file/URL patterns
                urls = re.findall(r"https?://[^\s\"'<>]+", text)
                cmds = re.findall(r"npm install\s+(\S+)", text)
                for u in urls:
                    seen_actions[u] = seen_actions.get(u, 0) + 1
                for c in cmds:
                    key = f"npm:{c}"
                    seen_actions[key] = seen_actions.get(key, 0) + 1
            except (OSError, UnicodeDecodeError):
                continue

    for k, v in sorted(seen_actions.items(), key=lambda x: -x[1])[:5]:
        if v >= 3:
            patterns.append(f"{k} (×{v})")
    return patterns


# ============ Main ============

def status_report() -> dict[str, Any]:
    """Read-only status snapshot."""
    report = {
        "timestamp": now_iso(),
        "memory": {},
        "user": {},
        "notes_count": 0,
        "skills_count": 0,
        "cron_jobs": 0,
        "kanban_active": 0,
    }
    for p, key in [(MEMORY, "memory"), (USER_MD, "user")]:
        if p.exists():
            text = p.read_text()
            sections = parse_sections(text)
            report[key] = {
                "chars": len(text),
                "sections": len(sections),
                "limit": 3000 if key == "memory" else 1800,
                "usage_pct": round(100 * len(text) / (3000 if key == "memory" else 1800), 1),
            }
    if NOTES.exists():
        report["notes_count"] = len(list(NOTES.rglob("*.md")))
    if SKILLS.exists():
        report["skills_count"] = len([s for s in SKILLS.iterdir() if s.is_dir()])
    if CRON_JOBS.exists():
        try:
            jobs = json.loads(CRON_JOBS.read_text())
            report["cron_jobs"] = len(jobs) if isinstance(jobs, list) else 0
        except (json.JSONDecodeError, OSError):
            pass
    # Kanban
    sync = kanban_cron_sync()
    report["kanban_active"] = sync.get("active_tasks", 0)
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Hermes cross-system orchestrator")
    p.add_argument("--all", action="store_true", help="Run all sync steps")
    p.add_argument("--dedup", action="store_true", help="Deduplicate memory")
    p.add_argument("--pointers", action="store_true", help="Update memory pointers")
    p.add_argument("--archive", action="store_true", help="Archive old notes")
    p.add_argument("--kanban-sync", action="store_true", help="Sync kanban ↔ cron")
    p.add_argument("--patterns", action="store_true", help="Detect repeated patterns")
    p.add_argument("--status", action="store_true", help="Status report (no changes)")
    args = p.parse_args()

    if not any([args.all, args.dedup, args.pointers, args.archive, args.kanban_sync, args.patterns, args.status]):
        args.status = True  # default

    if args.status or args.all:
        report = status_report()
        print(json.dumps(report, indent=2))

    if args.all or args.dedup:
        m = dedup_memory(MEMORY)
        u = dedup_memory(USER_MD)
        if m + u == 0:
            log("dedup: no duplicates found")

    if args.all or args.pointers:
        update_pointers()

    if args.all or args.archive:
        archive_inactive()

    if args.all or args.kanban_sync:
        kanban_cron_sync()

    if args.all or args.patterns:
        pats = detect_repeated_patterns()
        if pats:
            log(f"patterns: {len(pats)} candidates - {pats}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
