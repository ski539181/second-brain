#!/usr/bin/env python3
"""
test_suite.py - Test critical scripts (auto coverage check)

Tests 4 key scripts:
- vector_memory (search works)
- feedback_tracker (log/analyze)
- healthcheck (passes)
- verify_challenges (runs)

Output: ~/.hermes/test_results.json
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
SCRIPTS = HERMES / "scripts"
CACHE = HERMES / "cache"


TESTS = [
    {
        "name": "healthcheck",
        "script": "healthcheck.py",
        "args": [],
        "expect": "✅ All systems healthy",
        "timeout": 15,
    },
    {
        "name": "feedback_tracker",
        "script": "feedback_tracker.py",
        "args": [],
        "expect": "Feedback Tracker",
        "timeout": 10,
    },
    {
        "name": "verify_challenges",
        "script": "verify_challenges.py",
        "args": [],
        "expect": "Summary",
        "timeout": 60,
    },
    {
        "name": "metrics",
        "script": "metrics.py",
        "args": [],
        "expect": "คะแนนรวม",
        "timeout": 10,
    },
    {
        "name": "practice_queue_stats",
        "script": "practice_queue.py",
        "args": ["stats"],
        "expect": "Practice",
        "timeout": 5,
    },
    {
        "name": "auto_improve",
        "script": "auto_improve.py",
        "args": [],
        "expect": "Auto-improve",
        "timeout": 30,
    },
    {
        "name": "apply_fixes",
        "script": "apply_fixes.py",
        "args": [],
        "expect": "Apply fixes",
        "timeout": 10,
    },
    {
        "name": "spaced_notes",
        "script": "spaced_notes.py",
        "args": [],
        "expect": "Spaced Notes",
        "timeout": 5,
    },
    {
        "name": "self_eval",
        "script": "self_eval.py",
        "args": [],
        "expect": "Self-Evaluation",
        "timeout": 5,
    },
    {
        "name": "cross_session",
        "script": "cross_session.py",
        "args": [],
        "expect": "Cross-Session",
        "timeout": 5,
    },
    {
        "name": "pattern_mining",
        "script": "pattern_mining.py",
        "args": [],
        "expect": "Pattern Mining",
        "timeout": 10,
    },
    {
        "name": "weakest_focus",
        "script": "weakest_focus.py",
        "args": [],
        "expect": "Weakest",
        "timeout": 5,
    },
    {
        "name": "daily_synthesis",
        "script": "daily_synthesis.py",
        "args": ["--cheap"],
        "expect": "Daily Synthesis",
        "timeout": 10,
    },
    {
        "name": "vector_memory",
        "script": "vector_memory.py",
        "args": ["--search", "scraper"],
        "expect": "Search",
        "timeout": 30,
    },
]


def run_test(test):
    """Run one test, return (passed, error)."""
    try:
        result = subprocess.run(
            ["python3", str(SCRIPTS / test["script"]), *test["args"]],
            capture_output=True,
            text=True,
            timeout=test["timeout"],
        )
        if result.returncode != 0:
            return False, f"exit {result.returncode}: {result.stderr[:200]}"
        if test["expect"] not in result.stdout:
            return False, f"missing '{test['expect']}' in output"
        return True, "ok"
    except subprocess.TimeoutExpired:
        return False, f"timeout ({test['timeout']}s)"
    except Exception as e:
        return False, f"exception: {e}"


def main():
    print(f"🧪 Test Suite — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    results = []
    for test in TESTS:
        ok, msg = run_test(test)
        status = "✅" if ok else "❌"
        print(f"  {status} {test['name']} — {msg}")
        results.append({
            "name": test["name"],
            "passed": ok,
            "message": msg,
        })
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = passed / total * 100 if total else 0
    print(f"\n📊 Coverage: {passed}/{total} ({pct:.0f}%)")
    
    out = CACHE / "test_results.json"
    out.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "passed": passed,
        "total": total,
        "coverage_pct": pct,
        "results": results,
    }, indent=2, default=str))
    print(f"📄 Saved: {out}")
    return 0 if pct == 100 else 1


if __name__ == "__main__":
    exit(main())
