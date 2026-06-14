#!/usr/bin/env python3
"""
user_feedback.py - Weekly user feedback collection (addresses weakest area)

Cron: 0 18 * * 0 (Sunday 6 PM)
Sends to Telegram asking user to rate the week 1-10 + comment.
Stores response in feedback.json for analysis.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
CACHE = HERMES / "cache"
FEEDBACK_FILE = CACHE / "user_feedback.json"


def get_weekly_stats() -> dict:
    """Gather system stats for context."""
    stats = {"ts": datetime.now().isoformat()}
    # Test pass rate
    tr = CACHE / "test_results.json"
    if tr.exists():
        try:
            data = json.loads(tr.read_text())
            stats["tests"] = f"{data.get('pass', '?')}/{data.get('total', '?')}"
        except Exception:
            pass
    # Cron count
    cj = HERMES / "cron" / "jobs.json"
    if cj.exists():
        try:
            data = json.loads(cj.read_text())
            stats["crons"] = len(data.get("jobs", []))
        except Exception:
            pass
    return stats


def ask_via_telegram():
    """Send weekly feedback request to Telegram."""
    stats = get_weekly_stats()
    msg = (
        f"📊 **สรุปสัปดาห์นี้** ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        f"🧪 Tests: {stats.get('tests', '?')}\n"
        f"⏰ Crons: {stats.get('crons', '?')}\n"
        f"💾 Memory: managed\n\n"
        f"**คุณพอใจแค่ไหน?** (1-10)\n"
        f"ตอบ: `!rate 8` หรือ `!rate 5 ต้องปรับ X`"
    )
    try:
        from hermes_tools import send_message
        send_message(message=msg, target="telegram")
        print(f"✅ Sent weekly feedback request to Telegram")
    except Exception as e:
        print(f"⚠️  Could not send: {e}")
        # Save to file for later delivery
        (CACHE / "pending_feedback.txt").write_text(msg)


def save_response(rating: int, comment: str = ""):
    """Save user's feedback response."""
    if not FEEDBACK_FILE.exists():
        history = []
    else:
        try:
            history = json.loads(FEEDBACK_FILE.read_text())
        except Exception:
            history = []
    history.append({
        "ts": datetime.now().isoformat(),
        "rating": rating,
        "comment": comment,
    })
    # Keep last 12 weeks
    history = history[-12:]
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    print(f"✅ Saved: {rating}/10 — {comment[:50]}")


def show_history():
    """Show feedback history + trend."""
    if not FEEDBACK_FILE.exists():
        print("No feedback yet — will collect weekly")
        return
    history = json.loads(FEEDBACK_FILE.read_text())
    print(f"📊 Feedback History ({len(history)} weeks):\n")
    for h in history:
        bar = "█" * h["rating"] + "░" * (10 - h["rating"])
        print(f"  {h['ts'][:10]}  {h['rating']}/10  {bar}  {h.get('comment', '')[:50]}")
    if history:
        avg = sum(h["rating"] for h in history) / len(history)
        print(f"\n  Average: {avg:.1f}/10")
        trend = "↗" if len(history) >= 2 and history[-1]["rating"] > history[-2]["rating"] else (
            "↘" if len(history) >= 2 and history[-1]["rating"] < history[-2]["rating"] else "→"
        )
        print(f"  Trend: {trend}")


def main():
    if len(sys.argv) < 2:
        show_history()
        return
    cmd = sys.argv[1]
    if cmd == "--ask":
        ask_via_telegram()
    elif cmd == "--rate" and len(sys.argv) >= 3:
        try:
            rating = int(sys.argv[2])
            comment = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
            save_response(rating, comment)
        except ValueError:
            print("❌ rating must be 1-10")
    else:
        show_history()


if __name__ == "__main__":
    main()
