#!/usr/bin/env python3
"""
token_alarm.py - Alert if daily token cost exceeds threshold

Wraps token_counter.py with thresholds, alerts, and trend tracking.

Config (env or defaults):
  TOKEN_ALARM_DAILY=$0.50
  TOKEN_ALARM_HOURLY=$0.10
  TOKEN_ALERT_CHAT=telegram  (or "local")

Features:
- Per-day and per-hour thresholds
- Trend: 20% jump vs yesterday = alert
- Dry-run mode for testing
- Cost projection at current rate
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
LOG_FILE = HERMES / "logs" / "tokens.jsonl"

DAILY_THRESHOLD = float(os.environ.get("TOKEN_ALARM_DAILY", "0.50"))
HOURLY_THRESHOLD = float(os.environ.get("TOKEN_ALARM_HOURLY", "0.10"))
JUMP_THRESHOLD_PCT = 20  # alert if 20% jump


def get_today_cost():
    if not LOG_FILE.exists():
        return {"cost": 0, "in_tok": 0, "out_tok": 0, "calls": 0}
    today = datetime.now().strftime("%Y-%m-%d")
    in_tok = out_tok = calls = 0
    for line in LOG_FILE.read_text(errors="ignore").split("\n"):
        if not line.strip() or today not in line:
            continue
        try:
            e = json.loads(line)
            if e.get("direction") == "input":
                in_tok += e.get("tokens", 0)
            elif e.get("direction") == "output":
                out_tok += e.get("tokens", 0)
            calls += 1
        except Exception:
            continue
    # Cost calc (deepseek-v4-flash)
    cost = (in_tok / 1_000_000) * 0.14 + (out_tok / 1_000_000) * 0.28
    return {"cost": cost, "in_tok": in_tok, "out_tok": out_tok, "calls": calls}


def get_yesterday_cost():
    """Get yesterday's total cost for trend comparison."""
    if not LOG_FILE.exists():
        return 0
    yesterday = (datetime.now().timestamp() - 86400)
    yesterday_iso = datetime.fromtimestamp(yesterday).strftime("%Y-%m-%d")
    in_tok = out_tok = 0
    for line in LOG_FILE.read_text(errors="ignore").split("\n"):
        if not line.strip() or yesterday_iso not in line:
            continue
        try:
            e = json.loads(line)
            if e.get("direction") == "input":
                in_tok += e.get("tokens", 0)
            elif e.get("direction") == "output":
                out_tok += e.get("tokens", 0)
        except Exception:
            continue
    return (in_tok / 1_000_000) * 0.14 + (out_tok / 1_000_000) * 0.28


def project_daily(hourly_cost, current_hour):
    """Project end-of-day cost at current hourly rate."""
    if current_hour == 0:
        return hourly_cost * 24
    return (hourly_cost / current_hour) * 24


def main():
    dry_run = "--dry-run" in sys.argv
    today = get_today_cost()
    yesterday = get_yesterday_cost()
    current_hour = datetime.now().hour
    hourly_cost = today["cost"] / max(1, current_hour)
    projected = project_daily(hourly_cost, current_hour)

    alerts = []
    if today["cost"] > DAILY_THRESHOLD:
        alerts.append(f"💰 Daily cost ${today['cost']:.4f} > threshold ${DAILY_THRESHOLD}")
    if hourly_cost > HOURLY_THRESHOLD:
        alerts.append(f"⏰ Hourly rate ${hourly_cost:.4f} > threshold ${HOURLY_THRESHOLD}")
    if yesterday > 0:
        jump = ((today["cost"] - yesterday) / yesterday) * 100
        if jump > JUMP_THRESHOLD_PCT:
            alerts.append(f"📈 +{jump:.0f}% vs yesterday (${yesterday:.4f} → ${today['cost']:.4f})")
    if projected > DAILY_THRESHOLD * 2:
        alerts.append(f"🔮 Projected end-of-day: ${projected:.4f}")

    print(f"📊 Token Cost Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Today:    ${today['cost']:.4f} ({today['in_tok']:,} in + {today['out_tok']:,} out, {today['calls']} calls)")
    print(f"   Hourly:   ${hourly_cost:.4f}/hr")
    print(f"   Projected EOD: ${projected:.4f}")
    print(f"   Yesterday: ${yesterday:.4f}")
    if alerts:
        print(f"\n⚠️  {len(alerts)} alert(s):")
        for a in alerts:
            print(f"   {a}")
    else:
        print("\n✅ Within thresholds")

    if dry_run:
        print("\n[DRY-RUN: no alerts sent]")
    elif alerts:
        # Save alerts for next telegram send
        alert_file = HERMES / "logs" / "token-alerts.jsonl"
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        with open(alert_file, "a") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(), "alerts": alerts,
                                "cost": today["cost"]}) + "\n")
        print(f"\n📤 Alerts queued for next telegram send")

    return 1 if alerts else 0


if __name__ == "__main__":
    sys.exit(main())
