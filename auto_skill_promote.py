#!/usr/bin/env python3
"""
auto_skill_promote.py - Detect repeated patterns → suggest skill creation

Runs weekly (Sun 2 AM). Scans:
- Recent git commits (similar messages)
- Recent log files (repeated commands/URLs)
- Memory entries (frequent keywords)
- Session history (if accessible)

Output: notes/pattern-candidates.md with suggestions
"""
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CRON_OUT = HERMES / "cron" / "output"
CANDIDATES_FILE = NOTES / "pattern-candidates.md"


def scan_cron_outputs():
    """Find repeated patterns in recent cron outputs."""
    if not CRON_OUT.exists():
        return Counter()
    counter = Counter()
    cutoff = datetime.now() - timedelta(days=7)
    cutoff_ts = cutoff.timestamp()

    for log_file in CRON_OUT.rglob("*.md"):
        try:
            if log_file.stat().st_mtime < cutoff_ts:
                continue
            text = log_file.read_text(errors="ignore")
            # Extract URLs, commands, file paths
            urls = re.findall(r"https?://[^\s\"'<>]+", text)
            cmds = re.findall(r"(?:npm install|pip install|git push|sudo|cd /|chmod)\s+\S+", text)
            for u in urls:
                counter[f"URL: {u[:80]}"] += 1
            for c in cmds:
                counter[f"CMD: {c[:80]}"] += 1
        except (OSError, UnicodeDecodeError):
            continue
    return counter


def scan_git_recent():
    """Find repeated commit message patterns."""
    r = subprocess.run(
        ["git", "log", "--since=7 days ago", "--pretty=format:%s"],
        capture_output=True, text=True, timeout=10, cwd=NOTES
    )
    if not r.stdout:
        return Counter()
    # Group by first word
    counter = Counter()
    for line in r.stdout.strip().split("\n"):
        if line:
            prefix = line.split(":", 1)[0].strip()
            counter[f"commit:{prefix}"] += 1
    return counter


def main():
    print("🔍 Scanning for repeated patterns (7 days)...")

    cron_patterns = scan_cron_outputs()
    git_patterns = scan_git_recent()

    all_patterns = cron_patterns + git_patterns
    candidates = [(p, c) for p, c in all_patterns.most_common(20) if c >= 3]

    if not candidates:
        print("✅ No new pattern candidates (need 3+ occurrences)")
        return

    lines = [
        "# Pattern Candidates for Skill Promotion",
        "",
        f"Generated: {datetime.now().isoformat()}",
        "",
        f"Found **{len(candidates)}** patterns with 3+ occurrences in the last 7 days.",
        "",
        "## Candidates",
        "",
    ]
    for pattern, count in candidates:
        lines.append(f"- **{count}x** — `{pattern}`")

    lines += [
        "",
        "## Recommended action",
        "",
        "Review each candidate. If a pattern is reusable, ask the agent to create a skill:",
        '> "Save this as a skill"',
        "",
    ]
    CANDIDATES_FILE.write_text("\n".join(lines))
    print(f"✅ Wrote {len(candidates)} candidates to {CANDIDATES_FILE}")


if __name__ == "__main__":
    main()
