#!/usr/bin/env python3
"""
apply_fixes.py - Auto-apply safe fixes from auto-improve findings

What it does:
1. Add wikilinks to orphan notes (where concept is mentioned)
2. Add minimal docstrings to functions missing them
3. Skip dangerous operations (no file deletion, no mass renames)

Runs at 06:00 daily.
Token cost: 0 (Python only).
"""
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
SCRIPTS = HERMES / "scripts"
CACHE = HERMES / "cache"

COMMON_CONCEPTS = {
    "Cloudflare": "Cloudflare bypass", "Tiktoken": "Tiktoken tracking",
    "TokenRouter": "TokenRouter usage", "Orchestrator": "Orchestrator pattern",
    "FTScraper": "FTScraper usage", "Memory": "Memory management",
    "Cron": "Cron jobs", "Skill": "Skill creation",
    "WebScraper": "Web scraping", "Telegram": "Telegram bot",
    "Termux": "Termux environment", "Hermes": "Hermes Agent",
    "Patchright": "Patchright scraper", "curl_cffi": "curl_cffi bypass",
    "GitHub": "GitHub repo", "Second Brain": "Second Brain notes",
    "Obsidian": "Obsidian setup", "Karpathy": "Karpathy rules",
    "Deepseek": "DeepSeek model", "Oracle": "Oracle Cloud",
    "Mac": "Mac environment", "iPhone": "iPhone usage",
    "Automation": "Automation cron", "Daily": "Daily routine",
    "Healthcheck": "Health check", "Refactor": "Refactor code",
    "Performance": "Performance tuning", "Reflection": "Reflection journal",
    "Practice": "Practice queue", "Metrics": "Metrics dashboard",
    "Auto-improve": "Auto-improve system", "Wikilink": "Wikilink format",
    "Self-quiz": "Self-quiz engine", "Code smell": "Code smell detection",
}


def get_note_titles():
    titles = {}
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            text = f.read_text()
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            if m:
                titles[m.group(1).strip()] = f
        except Exception:
            pass
    return titles


def apply_wikilinks(limit=15):
    """Add [[wikilinks]] for first occurrence of each concept in orphan notes.

    Even if target note doesn't exist, creates dangling link for Obsidian
    to resolve later.
    """
    titles = get_note_titles()
    # Build reverse map: alias -> canonical title (case-insensitive)
    canonical = {k.lower(): k for k in titles.keys()}
    # Also build word index from titles (for fuzzy match)
    title_words = set()
    for k in titles:
        title_words.update(k.lower().split())

    fixes = []
    for title, fp in titles.items():
        try:
            text = fp.read_text()
        except Exception:
            continue
        if "[[" in text:
            continue
        # Try to add at most 2 wikilinks per note
        added = 0
        new_text = text
        for concept, target in COMMON_CONCEPTS.items():
            if added >= 3:
                break
            # If target exists as title, use it; else use concept itself
            target_title = target if target.lower() in canonical else concept
            if target_title.lower() == title.lower():
                continue
            # Find first occurrence
            pattern = re.compile(rf"\b{re.escape(concept)}\b", re.IGNORECASE)
            m = pattern.search(new_text)
            if m:
                new_text = new_text[:m.start()] + f"[[{target_title}]]" + new_text[m.end():]
                added += 1
                fixes.append({"note": title, "concept": concept, "target": target_title})
        if added > 0 and new_text != text:
            fp.write_text(new_text)
        if len(fixes) >= limit:
            break
    return fixes


def add_docstrings(limit=10):
    """Add minimal docstrings to functions missing them."""
    import ast
    fixes = []
    for f in SCRIPTS.glob("*.py"):
        if f.name.startswith("_"):
            continue
        try:
            source = f.read_text()
            tree = ast.parse(source)
        except Exception:
            continue

        lines = source.split("\n")
        modified = False

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_"):
                continue
            if ast.get_docstring(node):
                continue
            # Check what's after def line
            def_line = node.lineno  # 1-indexed
            next_line_idx = node.body[0].lineno - 1  # 0-indexed
            # If next line is already a docstring or has content, skip
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx].strip()
                if next_line.startswith('"""') or next_line.startswith("'''"):
                    continue
            # Insert docstring
            indent = "    " * (lines[def_line - 1].count("    ") + 1)  # rough indent
            docstring = f'{indent}"""{node.name} - TODO: describe."""'
            # Insert before first body statement
            lines.insert(next_line_idx, docstring)
            modified = True
            fixes.append({"file": f.name, "function": node.name})

        if modified and len(fixes) <= limit:
            f.write_text("\n".join(lines))

        if len(fixes) >= limit:
            break
    return fixes


def main():
    print(f"🔧 Apply fixes — {datetime.now().isoformat()}\n")
    
    # 1. Wikilinks
    wikilinks = apply_wikilinks()
    print(f"📝 Wikilinks added: {len(wikilinks)}")
    for w in wikilinks[:5]:
        print(f"   • {w['note']}: [[{w['target']}]]  (concept: {w['concept']})")
    
    # 2. Docstrings
    docstrings = add_docstrings()
    print(f"\n📄 Docstrings added: {len(docstrings)}")
    for d in docstrings[:5]:
        print(f"   • {d['file']}::{d['function']}()")
    
    # Save report
    out = CACHE / "fixes_applied.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at": datetime.now().isoformat(),
        "wikilinks": wikilinks,
        "docstrings": docstrings,
    }, indent=2, default=str))
    print(f"\n📄 Saved: {out}")
    return 0


if __name__ == "__main__":
    exit(main())
