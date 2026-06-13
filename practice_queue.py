#!/usr/bin/env python3
"""
practice_queue.py - Spaced repetition for coding challenges

Tracks:
- Pass/fail per challenge
- Time since last attempt
- Mastery score (0-100)

Picks next challenge to practice using spaced repetition:
- Failed → review often (next time)
- Mastered → review rarely (after many passes)
- New → priority high

Token cost: 0 (Python only)
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
STATE_FILE = HERMES / "cache" / "practice-queue.json"
CHALLENGES = HERMES / "notes" / "coding-challenges-45.md"

# Spaced repetition intervals (in days)
INTERVALS = {
    "failed": 0,        # review next time
    "new": 0,           # review next time
    "learning": 1,      # review tomorrow
    "reviewing": 3,     # review in 3 days
    "mastered": 14,     # review in 14 days
}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"challenges": {}, "history": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def parse_challenges():
    """Parse challenge file → {id: title}"""
    if not CHALLENGES.exists():
        return {}
    text = CHALLENGES.read_text()
    challenges = {}
    for m in re.finditer(r"^### (\d+)\.\s+(.+?)$", text, re.MULTILINE):
        challenges[int(m.group(1))] = m.group(2).strip()
    return challenges


def run_verifier():
    """Run the verifier and parse pass/fail."""
    r = subprocess.run(
        ["python3", str(HERMES / "scripts" / "verify_challenges.py")],
        capture_output=True, text=True, timeout=120
    )
    # Parse: ✅ Q N: title... (pass), ❌ Q N: title... (fail), ⏭️ Q N: title... (skip)
    results = {}
    for line in r.stdout.split("\n"):
        m = re.search(r"^\s*(?:✅|❌|⏭️)\s*Q\s*(\d+):", line)
        if m:
            pid = int(m.group(1))
            if "✅" in line[:5]:
                results[pid] = "pass"
            elif "❌" in line[:5]:
                results[pid] = "fail"
            elif "⏭️" in line[:5]:
                results[pid] = "skip"
    return results


def compute_mastery(state, results):
    """Update mastery scores based on new results."""
    now = datetime.now()
    challenges = parse_challenges()
    for pid, title in challenges.items():
        status = results.get(pid, "skip")
        key = str(pid)
        if key not in state["challenges"]:
            state["challenges"][key] = {
                "id": pid,
                "title": title,
                "status": "new",
                "mastery": 0,
                "attempts": 0,
                "passes": 0,
                "fails": 0,
                "last_attempt": None,
                "next_review": now.isoformat(),
            }
        c = state["challenges"][key]
        if status == "pass":
            c["passes"] += 1
            c["mastery"] = min(100, c["mastery"] + 20)
            c["status"] = "mastered" if c["mastery"] >= 80 else "reviewing" if c["mastery"] >= 40 else "learning"
        elif status == "fail":
            c["fails"] += 1
            c["mastery"] = max(0, c["mastery"] - 15)
            c["status"] = "learning"
        # skip = no change
        c["attempts"] += 1
        c["last_attempt"] = now.isoformat()
        # Compute next review
        days = INTERVALS.get(c["status"], 1)
        c["next_review"] = (now + timedelta(days=days)).isoformat()
    return state


def pick_next(state, count=3):
    """Pick next challenges to practice (priority: failed > new > reviewing > mastered)."""
    now = datetime.now()
    due = []
    for c in state["challenges"].values():
        nr = datetime.fromisoformat(c["next_review"])
        if nr <= now:
            # Priority: failed (0) < new (1) < learning (2) < reviewing (3) < mastered (4)
            priority = {"failed": 0, "new": 1, "learning": 2, "reviewing": 3, "mastered": 4}.get(c["status"], 1)
            # Boost failed/new
            if c["status"] in ("new",):
                priority -= 0.5
            due.append((priority, c["id"], c["title"], c["status"], c["mastery"]))
    due.sort()
    return due[:count]


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "queue"

    if action == "update":
        # Run verifier + update state
        print("🔄 Running verifier...")
        results = run_verifier()
        state = load_state()
        state = compute_mastery(state, results)
        state["history"].append({
            "timestamp": datetime.now().isoformat(),
            "results": results,
        })
        # Keep history to last 30 entries
        state["history"] = state["history"][-30:]
        save_state(state)
        p = sum(1 for v in results.values() if v == "pass")
        f = sum(1 for v in results.values() if v == "fail")
        s = sum(1 for v in results.values() if v == "skip")
        print(f"✅ Pass: {p}, ❌ Fail: {f}, ⏭️ Skip: {s}")
        print(f"📊 State saved: {STATE_FILE}")

    elif action == "queue":
        # Show next to practice
        state = load_state()
        next_challenges = pick_next(state)
        if not next_challenges:
            print("📭 No challenges due. Try again later.")
            return 0
        print(f"📚 Next {len(next_challenges)} challenges to practice:\n")
        for prio, pid, title, status, mastery in next_challenges:
            icon = {"new": "🆕", "learning": "📖", "reviewing": "🔄", "mastered": "✅"}.get(status, "?")
            print(f"  {icon} Q{pid:>2} [{status:<10}] mastery={mastery:>3}% — {title}")
        return 0

    elif action == "stats":
        state = load_state()
        challenges = state["challenges"]
        if not challenges:
            print("📊 No data. Run `update` first.")
            return 0
        total = len(challenges)
        by_status = {}
        for c in challenges.values():
            by_status[c["status"]] = by_status.get(c["status"], 0) + 1
        avg_mastery = sum(c["mastery"] for c in challenges.values()) / total
        total_attempts = sum(c["attempts"] for c in challenges.values())
        total_passes = sum(c["passes"] for c in challenges.values())
        print(f"📊 Practice queue stats:")
        print(f"   Total challenges: {total}")
        print(f"   Avg mastery: {avg_mastery:.1f}%")
        print(f"   Total attempts: {total_attempts}")
        print(f"   Pass rate: {total_passes/total_attempts*100:.1f}%" if total_attempts else "   No attempts")
        print(f"   By status:")
        for s, n in sorted(by_status.items()):
            print(f"     {s}: {n}")
        return 0

    elif action == "reset":
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        print("🗑️  State reset")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
