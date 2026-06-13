#!/usr/bin/env python3
"""
cron_health.py - Monitor cron job execution health

Verifies:
- Each enabled job ran within expected window
- No silent failures
- Jobs with errors get flagged

Runs hourly via cron.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
JOBS_FILE = HERMES / "cron" / "jobs.json"
ALERT_LOG = HERMES / "logs" / "cron-alerts.jsonl"


def parse_schedule(sched):
    if not isinstance(sched, dict):
        return None
    if sched.get("kind") == "interval":
        return sched.get("minutes", 60)
    if sched.get("kind") == "cron":
        expr = sched.get("expr", "")
        if "* * * * *" in expr:
            return 1
        if "0 * * * *" in expr or "@hourly" in expr:
            return 60
        if "0 0 * * *" in expr or "@daily" in expr:
            return 1440
        if "0 0 * * 0" in expr or "@weekly" in expr:
            return 10080
        return 60
    return None


def main():
    if not JOBS_FILE.exists():
        print("❌ jobs.json missing")
        return 1
    try:
        data = json.loads(JOBS_FILE.read_text())
    except Exception as e:
        print(f"❌ jobs.json unreadable: {e}")
        return 1

    jobs = data.get("jobs", data) if isinstance(data, dict) else data
    active = [j for j in jobs if j.get("enabled", True)]
    now = datetime.now()
    issues = []

    for job in active:
        name = job.get("name", "?")[:50]
        jid = job.get("job_id", "?")
        last_run = job.get("last_run_at")
        last_status = job.get("last_status")
        sched = job.get("schedule", {})
        interval_min = parse_schedule(sched)

        if not last_run:
            issues.append(f"⚠️  {jid[:10]}: never ran — {name}")
            continue
        try:
            last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00").replace("+00:00", ""))
        except Exception:
            continue
        age_min = (now - last_dt).total_seconds() / 60
        if interval_min and age_min > interval_min * 2:
            issues.append(f"⏰ {jid[:10]}: last ran {age_min:.0f}m ago (expected ≤{interval_min*2}m) — {name}")
        if last_status and last_status not in ("success", "completed", "ok", None):
            issues.append(f"❌ {jid[:10]}: last status={last_status} — {name}")

    print(f"🩺 Cron Health — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Active: {len(active)}")
    if issues:
        print(f"\n⚠️  {len(issues)} issue(s):")
        for i in issues:
            print(f"   {i}")
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERT_LOG, "a") as f:
            f.write(json.dumps({"ts": now.isoformat(), "issues": issues}) + "\n")
    else:
        print("   ✅ All jobs healthy")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
