#!/usr/bin/env python3
"""
monitor_cron_effort.py — Track reasoning_effort ใน cron outputs

ตรวจ cron output files → หา reasoning_tokens, effort, time
สรุปเป็น table ให้ user เห็นว่า crons ใช้ effort อะไรจริง
"""
import os, re, json, sys
from pathlib import Path
from datetime import datetime

OUT_DIR = Path("/root/.hermes/cron/output")
if not OUT_DIR.exists():
    print("❌ No cron output dir")
    sys.exit(1)

print("📊 Cron Effort Monitor")
print("=" * 70)
print(f"{'Cron':<25s} {'Time':<10s} {'Effort':<8s} {'rt':>5s} {'Notes'}")
print("-" * 70)

for cron_dir in sorted(OUT_DIR.iterdir()):
    if not cron_dir.is_dir():
        continue
    cron_name = cron_dir.name[:8]
    # Get most recent file
    files = sorted(cron_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        continue
    latest = files[0]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime).strftime("%H:%M")

    content = latest.read_text(errors="ignore")

    # Extract effort label
    eff_match = re.search(r"Effort:\s*(\w+)", content)
    effort = eff_match.group(1) if eff_match else "?"

    # Extract time / rt from response (if any)
    rt_match = re.search(r"reasoning_tokens[:\s]+(\d+)", content)
    rt = int(rt_match.group(1)) if rt_match else 0

    # Notes
    notes = ""
    if "นอนต่อ" in content or "😴" in content:
        notes = "no task"
    elif "✅" in content:
        notes = "task done"

    print(f"{cron_name:<25s} {mtime:<10s} {effort:<8s} {rt:>5d} {notes}")

print("=" * 70)
print("\n💡 rt = reasoning_tokens (from API usage)")
print("   effort = label agent ใส่เอง (low/medium/high)")
