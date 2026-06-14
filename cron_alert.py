#!/usr/bin/env python3
"""
cron_alert.py - Alert if any cron job failed (addresses ops gap)
Runs after each cron tick: checks exit codes, alerts on Telegram.
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
CRON_LOG = HERMES / "cron" / "output"
ALERT_FILE = HERMES / "cache" / "cron_alerts.json"


def check_recent_failures(minutes: int = 60) -> list:
    """Check for failed cron jobs in last N minutes."""
    if not CRON_LOG.exists():
        return []
    cutoff = time.time() - minutes * 60
    failures = []
    for job_dir in CRON_LOG.iterdir():
        if not job_dir.is_dir():
            continue
        for log in job_dir.glob("*.log"):
            try:
                mtime = log.stat().st_mtime
                if mtime < cutoff:
                    continue
                content = log.read_text(errors="ignore")
                # Detect failure indicators
                if any(indicator in content.lower() for indicator in [
                    "traceback", "error:", "exception:", "failed", "exit code: 1"
                ]):
                    failures.append({
                        "job": job_dir.name,
                        "log": log.name,
                        "ts": datetime.fromtimestamp(mtime).isoformat(),
                        "snippet": content[-300:],
                    })
            except Exception:
                pass
    return failures


def alert_via_telegram(failures: list):
    """Send alert to Telegram if failures found."""
    if not failures:
        return
    msg = f"🚨 **Cron Alert** — {len(failures)} failure(s):\n\n"
    for f in failures[:5]:  # max 5
        msg += f"❌ **{f['job']}** ({f['ts'][:19]})\n"
        msg += f"   `{f['snippet'][-100:]}`\n\n"
    try:
        from hermes_tools import send_message
        send_message(message=msg, target="telegram")
        print(f"✅ Alerted: {len(failures)} failure(s)")
    except Exception as e:
        print(f"⚠️  Could not alert: {e}")
        ALERT_FILE.write_text(json.dumps(failures, indent=2))


def main():
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    failures = check_recent_failures(minutes)
    if failures:
        print(f"⚠️  {len(failures)} cron failure(s) in last {minutes}min:")
        for f in failures:
            print(f"  - {f['job']}: {f['snippet'][:80]}")
        alert_via_telegram(failures)
    else:
        print(f"✅ No cron failures in last {minutes}min")


if __name__ == "__main__":
    main()
