#!/usr/bin/env python3
"""
morning_briefing.py - Run all systems in one go (integration!)

Combines:
- healthcheck (system status)
- daily_synthesis --llm (real AI analysis)
- cross_session --llm (topic analysis)
- vector_memory --llm (semantic search)
- self_eval --llm (quality analysis)
- practice_queue (challenges)
- metrics (composite score)
- test_suite (health)

Output: ~/.hermes/briefing/{date}.md
Token cost: ~$0.0001-0.0005 (3-5 LLM calls)
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
BRIEFING = HERMES / "briefing"
BRIEFING.mkdir(parents=True, exist_ok=True)

def run_cmd(name, cmd, timeout=60):
    """Run a command and return (success, output, error)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"timeout ({timeout}s)"
    except Exception as e:
        return False, "", str(e)


def section(title, emoji="📊"):
    print(f"\n{emoji} {title}")
    print("=" * 60)


def main():
    started = datetime.now()
    print(f"🌅 Morning Briefing — {started.strftime('%Y-%m-%d %H:%M')}\n")

    md = [f"# 🌅 Morning Briefing — {started.strftime('%Y-%m-%d %H:%M')}\n"]

    # 1. Health check
    section("Health Check", "🏥")
    ok, out, err = run_cmd("healthcheck", ["python3", str(HERMES/"scripts/healthcheck.py")], timeout=15)
    if ok:
        # Extract key lines
        for line in out.split("\n"):
            if "✅" in line or "⚠️" in line or "🔴" in line:
                print(f"  {line.strip()}")
        md.append("## 🏥 Health\n\n```\n" + out[:500] + "\n```\n")
    else:
        print(f"  ❌ Failed: {err[:100]}")
        md.append(f"## 🏥 Health\n\n❌ Failed: `{err[:200]}`\n")

    # 2. Metrics
    section("Metrics", "📊")
    ok, out, err = run_cmd("metrics", ["python3", str(HERMES/"scripts/metrics.py")], timeout=15)
    score_line = ""
    for line in out.split("\n"):
        if "Score" in line or "คะแนน" in line or "Mastery" in line or "Mastered" in line or "Pass" in line:
            print(f"  {line.strip()}")
            score_line += line.strip() + "\n"
    md.append("## 📊 Metrics\n\n" + score_line + "\n")

    # 3. Practice queue
    section("Practice Queue", "🎯")
    ok, out, err = run_cmd("practice", ["python3", str(HERMES/"scripts/practice_queue.py"), "stats"], timeout=30)
    practice_summary = ""
    for line in out.split("\n"):
        if any(x in line for x in ["Total", "Mastered", "Reviewing", "Learning", "Pass rate", "Avg mastery"]):
            print(f"  {line.strip()}")
            practice_summary += line.strip() + "\n"
    md.append("## 🎯 Practice\n\n" + practice_summary + "\n")

    # 4. LLM cross-session
    section("Cross-Session (LLM)", "🌐")
    ok, out, err = run_cmd("cross", ["python3", str(HERMES/"scripts/cross_session.py"), "--llm"], timeout=45)
    if ok:
        # Show LLM synthesis section
        in_synth = False
        synth_text = ""
        for line in out.split("\n"):
            if "LLM Cross-Session" in line:
                in_synth = True
                continue
            if in_synth:
                if line.strip() == "" or line.startswith("📄"):
                    in_synth = False
                else:
                    synth_text += line + "\n"
        if synth_text:
            print(f"  {synth_text[:300]}")
            md.append(f"## 🌐 Cross-Session (LLM)\n\n{synth_text}\n")
        else:
            print("  ℹ️ No LLM synthesis generated")
    else:
        print(f"  ❌ {err[:100]}")

    # 5. LLM daily synthesis
    section("Daily Synthesis (LLM)", "🧠")
    ok, out, err = run_cmd("synth", ["python3", str(HERMES/"scripts/daily_synthesis.py"), "--days", "3"], timeout=60)
    if ok:
        # Find latest synthesis file
        synth_dir = HERMES / "synthesis"
        if synth_dir.exists():
            files = sorted(synth_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
            if files:
                content = files[0].read_text()
                # Show first 400 chars
                print(f"  {content[:300]}")
                md.append(f"## 🧠 Daily Synthesis\n\n{content[:1500]}\n")

    # 6. Vector memory search (semantic)
    section("Vector Memory", "🧠")
    if "--no-search" not in sys.argv:
        ok, out, err = run_cmd("vec", ["python3", str(HERMES/"scripts/vector_memory.py")], timeout=30)
        if ok:
            for line in out.split("\n"):
                if "•" in line and ("scraper" in line or "memory" in line or "cron" in line or "skill" in line or "improvement" in line):
                    print(f"  {line.strip()}")

    # 7. Self-eval
    section("Self-Eval", "🎯")
    ok, out, err = run_cmd("eval", ["python3", str(HERMES/"scripts/self_eval.py")], timeout=20)
    for line in out.split("\n"):
        if "score" in line.lower() or "Sample" in line or "Average" in line:
            print(f"  {line.strip()}")

    # 8. Test suite
    section("Test Suite", "🧪")
    ok, out, err = run_cmd("test", ["python3", str(HERMES/"scripts/test_suite.py")], timeout=120)
    coverage = "?"
    for line in out.split("\n"):
        if "Coverage" in line:
            print(f"  {line.strip()}")
            coverage = line.strip()
    md.append(f"\n## 🧪 Test Coverage\n\n{coverage}\n")

    # Final
    elapsed = (datetime.now() - started).total_seconds()
    print(f"\n⏱️  Completed in {elapsed:.1f}s")

    # Save
    out_file = BRIEFING / f"{started.strftime('%Y-%m-%d')}.md"
    out_file.write_text("\n".join(md))
    print(f"📄 Saved: {out_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
