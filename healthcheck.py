#!/usr/bin/env python3
"""
healthcheck.py - System health check for Hermes

Runs every 6h via cron. Reports:
- Memory % usage
- Disk space
- GitHub sync status
- Cron job health
- Critical file presence

Exit 0 = all OK
Exit 1 = some checks failed
"""
import json
import subprocess
import sys
from pathlib import Path

HERMES = Path.home() / ".hermes"
ALERTS = []


def check_memory():
    for name, path, limit in [
        ("MEMORY.md", HERMES / "memories" / "MEMORY.md", 3000),
        ("USER.md", HERMES / "memories" / "USER.md", 1800),
    ]:
        if not path.exists():
            ALERTS.append(f"❌ {name} missing")
            continue
        # Use char count (UTF-8 chars), not bytes
        text = path.read_text(errors="ignore")
        size = len(text)
        pct = 100 * size / limit
        if pct > 90:
            ALERTS.append(f"⚠️  {name}: {pct:.0f}% ({size}/{limit} chars)")
        else:
            print(f"  ✅ {name}: {pct:.0f}% ({size}/{limit} chars)")
def check_disk():
    r = subprocess.run(["df", "-h", str(HERMES)], capture_output=True, text=True, timeout=10)
    lines = r.stdout.strip().split("\n")
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 5:
            use_pct = parts[4].rstrip("%")
            if int(use_pct) > 90:
                ALERTS.append(f"⚠️  Disk {use_pct}% full")
            else:
                print(f"  ✅ Disk: {use_pct}% used")

def check_github():
    r = subprocess.run(
        ["git", "log", "--oneline", "origin/main..HEAD"],
        capture_output=True, text=True, timeout=10, cwd=HERMES / "notes"
    )
    unpushed = r.stdout.strip()
    if unpushed:
        ALERTS.append(f"⚠️  {len(unpushed.split(chr(10)))} unpushed commits")
    else:
        print("  ✅ GitHub: synced")


def check_cron():
    jobs_file = HERMES / "cron" / "jobs.json"
    if not jobs_file.exists():
        ALERTS.append("❌ cron jobs.json missing")
        return
    try:
        data = json.loads(jobs_file.read_text())
        # jobs.json structure: {"jobs": [...], "updated_at": "..."}
        if isinstance(data, dict):
            jobs = data.get("jobs", [])
        else:
            jobs = data
        active = [j for j in jobs if j.get("enabled", True)]
        if len(active) < 3:
            ALERTS.append(f"⚠️  Only {len(active)} active cron jobs")
        else:
            print(f"  ✅ Cron: {len(active)} active jobs")
    except (json.JSONDecodeError, OSError):
        ALERTS.append("❌ cron jobs.json corrupt")


def check_critical_files():
    critical = [
        "scripts/orchestrator.py",
        "scripts/speed_toolbox.py",
        "skills/orchestrator/SKILL.md",
        "skills/speed-toolbox/SKILL.md",
    ]
    missing = [c for c in critical if not (HERMES / c).exists()]
    if missing:
        ALERTS.append(f"❌ Missing: {', '.join(missing)}")
    else:
        print(f"  ✅ All {len(critical)} critical files present")


def main():
    print("🏥 HERMES HEALTH CHECK")
    print("=" * 40)
    print("\n[Memory]")
    check_memory()
    print("\n[Disk]")
    check_disk()
    print("\n[GitHub]")
    check_github()
    print("\n[Cron]")
    check_cron()
    print("\n[Files]")
    check_critical_files()
    print()
    if ALERTS:
        print(f"⚠️  {len(ALERTS)} alert(s):")
        for a in ALERTS:
            print(f"  {a}")
        return 1
    print("✅ All systems healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
