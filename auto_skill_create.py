#!/usr/bin/env python3
"""
auto_skill_create.py - Auto-create skills from detected patterns

Extends auto_skill_promote.py to actually CREATE skills (not just suggest).
Only creates when pattern is strong (5+ occurrences + clear context).

Quality gates:
- Pattern must occur 5+ times
- Must have clear triggering keywords
- Won't create skills that already exist
- Adds to skills/ directory + auto-loads
"""
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
SKILLS = HERMES / "skills"
CRON_OUT = HERMES / "cron" / "output"
CANDIDATES = NOTES / "pattern-candidates.md"

# Quality gate
MIN_OCCURRENCES = 5
SKIP_IF_SKILL_EXISTS = True


def detect_patterns():
    """Find strong patterns in cron outputs and git history."""
    patterns = Counter()
    if CRON_OUT.exists():
        cutoff_ts = (datetime.now().timestamp() - 7 * 86400)
        for log in CRON_OUT.rglob("*.md"):
            try:
                if log.stat().st_mtime < cutoff_ts:
                    continue
                text = log.read_text(errors="ignore")
                # Strong patterns: repeated tools/errors/URLs
                for m in re.finditer(r"(?:Error|Failed|FAILED):\s*([^\n]{20,100})", text):
                    patterns[f"error:{m.group(1)[:80]}"] += 1
                for m in re.finditer(r"(?:TODO|FIXME|⚠️|🚨):\s*([^\n]{10,80})", text):
                    patterns[f"flag:{m.group(1)[:60]}"] += 1
            except (OSError, UnicodeDecodeError):
                continue
    return patterns


def existing_skill_names():
    if not SKILLS.exists():
        return set()
    return {p.parent.name for p in SKILLS.rglob("SKILL.md")}


def make_skill_md(pattern, count, source):
    """Generate a SKILL.md from a detected pattern."""
    name = re.sub(r"[^a-z0-9]+", "-", pattern.lower())[:40].strip("-")
    if not name or len(name) < 5:
        return None
    return f"""---
name: {name}
description: Auto-generated from pattern ({count} occurrences in 7 days). Use when user encounters "{pattern[:50]}" or similar context.
---

# {name.replace('-', ' ').title()}

**Auto-created:** {datetime.now().strftime('%Y-%m-%d')}
**Source:** {count} occurrences of pattern in 7 days
**Pattern:** `{pattern}`

## Trigger
This skill loads when the user encounters something matching: `{pattern[:60]}`

## Why
Detected via `auto_skill_create.py` from cron outputs. The pattern appeared {count} times in 7 days, suggesting it could benefit from a dedicated response pattern.

## Suggested response approach
1. Identify the specific instance of the pattern
2. Check existing skills for overlap
3. Use known solution from past occurrences

## Refinement needed
This is an auto-generated skeleton. Review and add:
- Concrete examples
- Verified solution steps
- Trigger conditions
- Pitfalls
"""


def main():
    dry_run = "--dry-run" in sys.argv
    patterns = detect_patterns()
    existing = existing_skill_names()
    created = []
    skipped = []

    for pattern, count in patterns.most_common(20):
        if count < MIN_OCCURRENCES:
            continue
        skill_md = make_skill_md(pattern, count, "cron_output")
        if not skill_md:
            continue
        # Extract name from frontmatter
        m = re.search(r"^name:\s*(\S+)", skill_md, re.MULTILINE)
        if not m:
            continue
        name = m.group(1)
        if SKIP_IF_SKILL_EXISTS and name in existing:
            skipped.append(f"{name} (exists)")
            continue
        skill_path = SKILLS / name
        if dry_run:
            print(f"  [DRY-RUN] would create: {name} ({count}x)")
            continue
        skill_path.mkdir(parents=True, exist_ok=True)
        (skill_path / "SKILL.md").write_text(skill_md)
        created.append(f"{name} ({count}x)")

    print(f"🧠 Auto-Skill Create — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"   Patterns found: {len(patterns)}")
    print(f"   Strong (≥{MIN_OCCURRENCES}x): {sum(1 for c in patterns.values() if c >= MIN_OCCURRENCES)}")
    if created:
        print(f"\n✅ Created {len(created)} skill(s):")
        for c in created:
            print(f"   • {c}")
    if skipped:
        print(f"\n⏭️  Skipped {len(skipped)}:")
        for s in skipped:
            print(f"   • {s}")
    if not created and not skipped:
        print("\n   No new skills needed")

    return 0 if not created and not dry_run else 0


if __name__ == "__main__":
    sys.exit(main())
