#!/usr/bin/env python3
"""
send_briefing.py - Send morning/weekly briefing to Telegram

Reads latest briefing file, formats compact version, sends to user's Telegram.
Called by cron after morning_briefing.py / weekly_report.py

Token cost: 0 (send only, no LLM)
"""
import os
import sys
import re
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
BRIEFING = HERMES / "briefing"

# Read Telegram target from user profile
USER_FILE = HERMES / "memories" / "USER.md"


def get_telegram_target():
    """Get user's Telegram chat ID from env or config."""
    # Try env first
    target = os.environ.get("TELEGRAM_HOME")
    if target:
        return target
    # Default: home channel
    return "telegram"  # Hermes will use home channel


def format_compact_briefing(briefing_path):
    """Extract key metrics from briefing file for compact Telegram view."""
    if not briefing_path.exists():
        return None
    content = briefing_path.read_text()
    lines = []

    # Header
    title_match = re.search(r'# 🌅 Morning Briefing — (.+)', content)
    if title_match:
        lines.append(f"🌅 **{title_match.group(1)}**")
    else:
        lines.append("🌅 **Briefing**")

    # Health - extract first 3 ✅/⚠️/🟢/🔴 lines
    health_section = re.search(r'## 🏥 Health\n\n```\n(.+?)\n```', content, re.DOTALL)
    if health_section:
        h_lines = [l.strip() for l in health_section.group(1).split('\n') if '✅' in l or '⚠️' in l or '🟢' in l or '🔴' in l][:4]
        if h_lines:
            lines.append("\n🏥 " + " | ".join(l.replace('  ', ' ').strip()[:30] for l in h_lines))

    # Metrics
    score_match = re.search(r'คะแนนรวม: ([\d.]+)/100', content)
    if score_match:
        lines.append(f"\n📊 Score: **{score_match.group(1)}/100**")

    # Practice
    mastery_match = re.search(r'Avg mastery: ([\d.]+%)', content)
    pass_match = re.search(r'Pass rate: ([\d.]+%)', content)
    if mastery_match and pass_match:
        lines.append(f"🎯 Mastery: {mastery_match.group(1)} | Pass: {pass_match.group(1)}")

    # Tests
    cov_match = re.search(r'Coverage: (\d+/\d+ \(\d+%\))', content)
    if cov_match:
        lines.append(f"🧪 Tests: **{cov_match.group(1)}**")

    # LLM synthesis - look for ## 💡 sections in synthesis content
    insight_match = re.search(r'## 💡[^\n]*\n\n?(.+?)(?:\n##|\Z)', content, re.DOTALL)
    if insight_match:
        insight = insight_match.group(1).strip()[:400]
        lines.append(f"\n💡 **Insight:**\n{insight}")

    return '\n'.join(lines)


def main():
    print(f"📤 Send Briefing — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Find latest briefing
    today = datetime.now().strftime('%Y-%m-%d')
    bp = BRIEFING / f"{today}.md"
    if not bp.exists():
        files = sorted(BRIEFING.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            print("❌ No briefing file found")
            return 1
        bp = files[0]
        print(f"  ℹ️  Using latest: {bp.name}")

    msg = format_compact_briefing(bp)
    if not msg:
        print("❌ Could not parse briefing")
        return 1

    # Print preview
    print("📝 Preview:")
    print("=" * 40)
    print(msg)
    print("=" * 40)

    # Try to send via send_message tool (works in agent context)
    try:
        from hermes_tools import send_message
        target = get_telegram_target()
        send_message(action="send", target=target, message=msg)
        print(f"\n✅ Sent to {target}")
    except Exception as e:
        print(f"\n⚠️  send_message not available in this context: {e}")
        # Fallback: save to send-queue for cron to pick up
        queue = HERMES / "cache" / "send_queue"
        queue.mkdir(parents=True, exist_ok=True)
        qf = queue / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        qf.write_text(msg)
        print(f"📥 Queued: {qf}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
