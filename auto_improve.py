#!/usr/bin/env python3
"""
auto_improve.py - Autonomous self-improvement

Runs periodically to:
1. Suggest wikilinks for orphan notes
2. Generate self-quiz questions from notes
3. Detect patterns → suggest new skills
4. Update knowledge graph

No user input needed.

Token cost: 0 (Python only)
"""
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
SKILLS = HERMES / "skills"

# Common concepts that should be linked
COMMON_CONCEPTS = {
    "Cloudflare": "Cloudflare bypass",
    "Tiktoken": "Tiktoken tracking",
    "TokenRouter": "TokenRouter usage",
    "Orchestrator": "Orchestrator pattern",
    "FTScraper": "FTScraper usage",
    "Wikilink": "Note linking",
    "Memory": "Memory management",
    "Cron": "Cron jobs",
    "Skill": "Skill creation",
    "WebScraper": "Web scraping",
    "Telegram": "Telegram bot",
    "Termux": "Termux environment",
    "Hermes": "Hermes Agent",
    "Patchright": "Patchright scraper",
    "Camoufox": "Camoufox browser",
    "curl_cffi": "curl_cffi bypass",
    "CF": "Cloudflare bypass",
    "API": "API integration",
    "GitHub": "GitHub repo",
    "Second Brain": "Second Brain notes",
    "Obsidian": "Obsidian setup",
    "Karpathy": "Karpathy rules",
    "Deepseek": "DeepSeek model",
    "Free Tier": "Free tier usage",
    "Oracle": "Oracle Cloud",
    "Mac": "Mac environment",
    "iPhone": "iPhone usage",
    "Automation": "Automation cron",
    "Daily": "Daily routine",
    "Healthcheck": "Health check",
    "Refactor": "Refactor code",
    "Performance": "Performance tuning",
}


def extract_concepts(text):
    """Find concept mentions in note text."""
    found = set()
    for concept in COMMON_CONCEPTS:
        # Case-insensitive match, word boundary
        if re.search(rf"\b{re.escape(concept)}\b", text, re.IGNORECASE):
            found.add(concept)
    return found


def get_all_titles():
    """Get all note titles (first H1)."""
    titles = {}
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            text = f.read_text()
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            if m:
                title = m.group(1).strip()
                titles[title] = f
        except Exception:
            pass
    return titles


def suggest_wikilinks(limit=10):
    """Find notes that could benefit from wikilinks."""
    titles = get_all_titles()
    suggestions = []
    for title, filepath in titles.items():
        try:
            text = filepath.read_text()
        except Exception:
            continue
        # Skip if already has wikilinks
        if "[[" in text:
            continue
        # Find concepts mentioned
        concepts = extract_concepts(text)
        for c in concepts:
            if c.lower() != title.lower():  # Don't self-link
                suggestions.append({
                    "note": title,
                    "file": filepath.name,
                    "concept": c,
                    "link_target": COMMON_CONCEPTS[c],
                })
                if len(suggestions) >= limit:
                    return suggestions
    return suggestions


def detect_repeated_patterns():
    """Look at recent log files for repeated patterns."""
    # Read tokens log for direction counts
    log = HERMES / "logs" / "tokens.jsonl"
    if not log.exists():
        return []
    directions = Counter()
    for line in log.read_text().splitlines():
        try:
            entry = json.loads(line)
            d = entry.get("direction", "unknown")
            directions[d] += 1
        except Exception:
            pass
    return directions.most_common(5)


def self_quiz_questions(limit=3):
    """Generate self-quiz questions from notes (heuristic)."""
    titles = list(get_all_titles().keys())
    # Pick random sample
    import random
    random.seed(datetime.now().strftime("%Y%m%d"))  # Same questions per day
    sample = random.sample(titles, min(limit, len(titles)))
    questions = []
    for title in sample:
        # Generate "what is X?" question
        questions.append({
            "question": f"อธิบาย '{title}' ใน 2-3 ประโยค",
            "source": title,
            "type": "recall",
        })
    return questions


def find_gaps():
    """Find notes that haven't been touched in 30+ days."""
    if not NOTES.exists():
        return []
    from datetime import timedelta
    threshold = datetime.now() - timedelta(days=30)
    stale = []
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < threshold:
                stale.append({"file": f.name, "last_modified": mtime.isoformat()})
        except Exception:
            pass
    return stale[:10]


def main():
    print(f"🧠 Auto-improve — {datetime.now().isoformat()}\n")
    
    # 1. Wikilink suggestions
    suggestions = suggest_wikilinks()
    print(f"📝 Wikilink suggestions: {len(suggestions)} notes need links")
    for s in suggestions[:5]:
        print(f"   • {s['note']} → [[{s['link_target']}]]  (mentions '{s['concept']}')")
    
    # 2. Pattern detection
    patterns = detect_repeated_patterns()
    print(f"\n🔍 Token patterns: {patterns}")
    
    # 3. Self-quiz
    quiz = self_quiz_questions()
    print(f"\n❓ Self-quiz (3 questions for today):")
    for q in quiz:
        print(f"   • {q['question']}  (source: {q['source']})")
    
    # 4. Stale notes
    stale = find_gaps()
    print(f"\n📅 Stale notes (>30 days): {len(stale)}")
    for s in stale[:3]:
        print(f"   • {s['file']}  (last: {s['last_modified'][:10]})")
    
    # Save report
    report = {
        "generated_at": datetime.now().isoformat(),
        "wikilink_suggestions": suggestions,
        "token_patterns": dict(patterns),
        "self_quiz": quiz,
        "stale_notes": stale,
    }
    out = CACHE / "auto_improve.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n📄 Saved: {out}")
    return 0


if __name__ == "__main__":
    exit(main())
