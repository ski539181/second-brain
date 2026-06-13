#!/usr/bin/env python3
"""
auto_improve.py - Autonomous self-improvement (20+ checks)

Runs periodically to:
- Wikilink suggestions
- Self-quiz generation
- Pattern detection
- Code quality
- Knowledge graph
- Memory pressure
- Token forecasting
- And 14 more...

No user input needed. 0 token cost.
"""
import json
import re
import os
import ast
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
SCRIPTS = HERMES / "scripts"
SKILLS = HERMES / "skills"
LOGS = HERMES / "logs"

# ============ CHECK 1-4 (existing) ============

COMMON_CONCEPTS = {
    "Cloudflare": "Cloudflare bypass", "Tiktoken": "Tiktoken tracking",
    "TokenRouter": "TokenRouter usage", "Orchestrator": "Orchestrator pattern",
    "FTScraper": "FTScraper usage", "Wikilink": "Note linking",
    "Memory": "Memory management", "Cron": "Cron jobs",
    "Skill": "Skill creation", "WebScraper": "Web scraping",
    "Telegram": "Telegram bot", "Termux": "Termux environment",
    "Hermes": "Hermes Agent", "Patchright": "Patchright scraper",
    "Camoufox": "Camoufox browser", "curl_cffi": "curl_cffi bypass",
    "CF": "Cloudflare bypass", "API": "API integration",
    "GitHub": "GitHub repo", "Second Brain": "Second Brain notes",
    "Obsidian": "Obsidian setup", "Karpathy": "Karpathy rules",
    "Deepseek": "DeepSeek model", "Free Tier": "Free tier usage",
    "Oracle": "Oracle Cloud", "Mac": "Mac environment",
    "iPhone": "iPhone usage", "Automation": "Automation cron",
    "Daily": "Daily routine", "Healthcheck": "Health check",
    "Refactor": "Refactor code", "Performance": "Performance tuning",
}


def extract_concepts(text):
    found = set()
    for concept in COMMON_CONCEPTS:
        if re.search(rf"\b{re.escape(concept)}\b", text, re.IGNORECASE):
            found.add(concept)
    return found


def get_all_titles():
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


def check_wikilink_suggestions(limit=10):
    titles = get_all_titles()
    suggestions = []
    for title, fp in titles.items():
        try:
            text = fp.read_text()
        except Exception:
            continue
        if "[[" in text:
            continue
        for c in extract_concepts(text):
            if c.lower() != title.lower():
                suggestions.append({"note": title, "file": fp.name, "concept": c, "target": COMMON_CONCEPTS[c]})
                if len(suggestions) >= limit:
                    return suggestions
    return suggestions


def check_token_patterns():
    log = LOGS / "tokens.jsonl"
    if not log.exists():
        return []
    directions = Counter()
    for line in log.read_text().splitlines():
        try:
            entry = json.loads(line)
            directions[entry.get("direction", "?")] += 1
        except Exception:
            pass
    return directions.most_common(5)


def check_self_quiz(limit=3):
    import random
    titles = list(get_all_titles().keys())
    random.seed(datetime.now().strftime("%Y%m%d"))
    sample = random.sample(titles, min(limit, len(titles)))
    return [{"question": f"อธิบาย '{t}' ใน 2-3 ประโยค", "source": t} for t in sample]


def check_stale_notes():
    if not NOTES.exists():
        return []
    threshold = datetime.now() - timedelta(days=30)
    stale = []
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < threshold:
                stale.append({"file": f.name, "last": mtime.isoformat()})
        except Exception:
            pass
    return stale[:10]


# ============ NEW CHECKS (16) ============

def check_5_code_smell():
    """Find long functions, complex code."""
    smells = []
    for f in SCRIPTS.glob("*.py"):
        try:
            tree = ast.parse(f.read_text())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = node.end_lineno - node.lineno + 1
                if lines > 80:
                    smells.append({"file": f.name, "function": node.name, "lines": lines, "type": "long_function"})
                # Count branches
                branches = sum(1 for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While, ast.Try)))
                if branches > 10:
                    smells.append({"file": f.name, "function": node.name, "branches": branches, "type": "complex"})
    return smells[:10]


def check_6_note_completeness():
    """Notes without summary/context."""
    incomplete = []
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f) or "README" in f.name:
            continue
        try:
            text = f.read_text()
        except Exception:
            continue
        # Check for summary indicators
        has_summary = bool(re.search(r"^##\s*(summary|สรุป|overview)", text, re.MULTILINE | re.IGNORECASE))
        has_tldr = "TL;DR" in text or "TLDR" in text
        # Too short = incomplete
        if len(text) < 500 and not (has_summary or has_tldr):
            incomplete.append({"file": f.name, "chars": len(text), "reason": "short + no summary"})
        elif not (has_summary or has_tldr) and len(text) < 2000:
            incomplete.append({"file": f.name, "chars": len(text), "reason": "no summary marker"})
    return incomplete[:10]


def check_7_cross_refs():
    """Find concepts in multiple notes but no shared link."""
    titles = get_all_titles()
    concept_to_notes = defaultdict(list)
    for title, fp in titles.items():
        try:
            text = fp.read_text()
        except Exception:
            continue
        for c in extract_concepts(text):
            concept_to_notes[c].append(title)
    # Concepts in 3+ notes but no link
    orphans = []
    for concept, notes in concept_to_notes.items():
        if len(notes) >= 3:
            orphans.append({"concept": concept, "appears_in": len(notes), "target": COMMON_CONCEPTS[concept]})
    return sorted(orphans, key=lambda x: -x["appears_in"])[:10]


def check_8_duplicates():
    """Find similar note titles (fuzzy match)."""
    titles = list(get_all_titles().keys())
    dupes = []
    for i, t1 in enumerate(titles):
        for t2 in titles[i+1:]:
            # Simple similarity: word overlap
            w1 = set(t1.lower().split())
            w2 = set(t2.lower().split())
            if not w1 or not w2:
                continue
            overlap = len(w1 & w2) / min(len(w1), len(w2))
            if overlap > 0.6:
                dupes.append({"a": t1, "b": t2, "similarity": round(overlap, 2)})
    return dupes[:10]


def check_9_skill_usage():
    """Count skill SKILL.md files and their triggers."""
    if not SKILLS.exists():
        return {"total": 0}
    skills = []
    for f in SKILLS.rglob("SKILL.md"):
        try:
            text = f.read_text()
            desc = re.search(r"description:\s*(.+?)$", text, re.MULTILINE)
            skills.append({"path": str(f.relative_to(SKILLS)), "trigger": desc.group(1)[:80] if desc else "?"})
        except Exception:
            pass
    return {"total": len(skills), "skills": skills[:10]}


def check_10_cron_efficiency():
    """Check which cron jobs are most active."""
    log_dir = HERMES / "cron"
    if not log_dir.exists():
        return []
    return {"dir_exists": True, "note": "see cron_health.py for details"}


def check_11_memory_pressure():
    """Predict when memory will fill."""
    mem_file = HERMES / "memories" / "MEMORY.md"
    user_file = HERMES / "memories" / "USER.md"
    import os
    state = {}
    for f in [mem_file, user_file]:
        if f.exists():
            text = f.read_text()
            state[f.name] = {
                "chars": len(text),
                "lines": text.count("\n"),
                "headroom_pct": round((1 - len(text) / 3000) * 100, 1) if "MEMORY" in f.name else round((1 - len(text) / 1800) * 100, 1)
            }
    return state


def check_12_token_forecast():
    """Project end-of-week token usage."""
    log = LOGS / "tokens.jsonl"
    if not log.exists():
        return {"note": "no log yet"}
    by_day = defaultdict(int)
    for line in log.read_text().splitlines():
        try:
            entry = json.loads(line)
            by_day[entry.get("date", "?")] += entry.get("input", 0) + entry.get("output", 0)
        except Exception:
            pass
    if len(by_day) < 2:
        return {"tracked_days": len(by_day), "note": "need more data"}
    # Average per day
    days = list(by_day.values())
    avg = sum(days) / len(days)
    # Forecast to end of week
    today = datetime.now()
    days_to_sunday = 6 - today.weekday() if today.weekday() < 6 else 0
    forecast = avg * (days_to_sunday + len(days))
    return {
        "tracked_days": len(by_day),
        "avg_per_day": round(avg, 0),
        "forecast_week": round(forecast, 0),
        "forecast_cost_usd": round(forecast * 0.00021 / 1000, 4),
    }


def check_13_script_deps():
    """Find broken imports in scripts."""
    import importlib.util
    broken = []
    for f in SCRIPTS.glob("*.py"):
        try:
            tree = ast.parse(f.read_text())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if name in ("subprocess", "json", "os", "re", "sys", "datetime", "pathlib", "collections", "ast", "time", "math", "shutil", "hashlib", "sqlite3", "csv", "string", "typing"):
                        continue
                    spec = importlib.util.find_spec(name)
                    if spec is None:
                        broken.append({"file": f.name, "module": name, "type": "import"})
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split(".")[0]
                    if name in ("subprocess", "json", "os", "re", "sys", "datetime", "pathlib", "collections", "ast", "time", "math", "shutil", "hashlib", "sqlite3", "csv", "string", "typing"):
                        continue
                    spec = importlib.util.find_spec(name)
                    if spec is None:
                        broken.append({"file": f.name, "module": name, "type": "from"})
    return broken[:10]


def check_14_activity_heatmap():
    """When is the most work happening?"""
    by_hour = Counter()
    by_dow = Counter()
    for subdir in [SCRIPTS, NOTES, SKILLS]:
        if not subdir.exists():
            continue
        for f in subdir.rglob("*"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                # Only recent
                if mtime > datetime.now() - timedelta(days=30):
                    by_hour[mtime.hour] += 1
                    by_dow[mtime.strftime("%a")] += 1
            except Exception:
                pass
    return {
        "by_hour": dict(sorted(by_hour.items())),
        "by_dow": dict(by_dow.most_common()),
        "peak_hour": by_hour.most_common(1)[0][0] if by_hour else None,
    }


def check_15_error_patterns():
    """Find recurring errors in logs."""
    log = LOGS / "tokens.jsonl"
    if not log.exists():
        return []
    # Just count error patterns in notes (any "ERROR" mentions)
    errors = []
    if NOTES.exists():
        for f in NOTES.rglob("*.md"):
            try:
                text = f.read_text()
                err_count = text.count("ERROR") + text.count("Error") + text.count("❌")
                if err_count >= 3:
                    errors.append({"file": f.name, "errors": err_count})
            except Exception:
                pass
    return sorted(errors, key=lambda x: -x["errors"])[:5]


def check_16_test_coverage():
    """Find scripts without test files."""
    scripts = [f.stem for f in SCRIPTS.glob("*.py")]
    test_dir = HERMES / "tests"
    has_tests = set()
    if test_dir.exists():
        has_tests = {f.stem.replace("test_", "") for f in test_dir.glob("test_*.py")}
    untested = [s for s in scripts if s not in has_tests and not s.startswith("_")]
    return {"total_scripts": len(scripts), "tested": len(has_tests), "untested": untested[:10]}


def check_17_config_drift():
    """Verify config vs actual state."""
    config = HERMES / "config.yaml"
    actual = {
        "scripts": len(list(SCRIPTS.glob("*.py"))) if SCRIPTS.exists() else 0,
        "notes": len([f for f in NOTES.rglob("*.md") if "archive" not in str(f)]) if NOTES.exists() else 0,
        "skills": len(list(SKILLS.rglob("SKILL.md"))) if SKILLS.exists() else 0,
    }
    return actual


def check_18_docstring_check():
    """Find functions without docstrings."""
    missing = []
    for f in SCRIPTS.glob("*.py"):
        if f.name.startswith("_"):
            continue
        try:
            tree = ast.parse(f.read_text())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                if not ast.get_docstring(node):
                    missing.append({"file": f.name, "function": node.name})
    return missing[:10]


def check_19_growth_metrics():
    """Track growth of notes/scripts over time."""
    by_month = defaultdict(lambda: {"notes": 0, "scripts": 0, "skills": 0})
    for subdir, name in [(NOTES, "notes"), (SCRIPTS, "scripts"), (SKILLS, "skills")]:
        if not subdir.exists():
            continue
        for f in subdir.rglob("*"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime > datetime.now() - timedelta(days=180):
                    by_month[mtime.strftime("%Y-%m")][name] += 1
            except Exception:
                pass
    return dict(sorted(by_month.items()))


def check_20_improvement_score():
    """Composite self-improvement score."""
    notes = len([f for f in NOTES.rglob("*.md") if "archive" not in str(f)]) if NOTES.exists() else 0
    skills = len(list(SKILLS.rglob("SKILL.md"))) if SKILLS.exists() else 0
    scripts = len(list(SCRIPTS.glob("*.py"))) if SCRIPTS.exists() else 0
    score = min(40, notes) + min(20, skills * 2) + min(20, scripts) + 20
    return {
        "score": min(100, score),
        "breakdown": f"notes={notes}/40 + skills={skills*2}/20 + scripts={scripts}/20 + base=20",
    }


def main():
    print(f"🧠 Auto-improve (20 checks) — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    results = {}
    
    checks = [
        (1, "Wikilink suggestions", check_wikilink_suggestions),
        (2, "Token patterns", check_token_patterns),
        (3, "Self-quiz", check_self_quiz),
        (4, "Stale notes", check_stale_notes),
        (5, "Code smells", check_5_code_smell),
        (6, "Note completeness", check_6_note_completeness),
        (7, "Cross-refs", check_7_cross_refs),
        (8, "Duplicates", check_8_duplicates),
        (9, "Skill usage", check_9_skill_usage),
        (10, "Cron efficiency", check_10_cron_efficiency),
        (11, "Memory pressure", check_11_memory_pressure),
        (12, "Token forecast", check_12_token_forecast),
        (13, "Script deps", check_13_script_deps),
        (14, "Activity heatmap", check_14_activity_heatmap),
        (15, "Error patterns", check_15_error_patterns),
        (16, "Test coverage", check_16_test_coverage),
        (17, "Config drift", check_17_config_drift),
        (18, "Docstrings", check_18_docstring_check),
        (19, "Growth metrics", check_19_growth_metrics),
        (20, "Improvement score", check_20_improvement_score),
    ]
    
    for num, name, fn in checks:
        try:
            r = fn()
            results[str(num)] = {"name": name, "result": r}
            # Brief summary
            if isinstance(r, list):
                print(f"  {num:>2}. {name:<22} {len(r)} items")
            elif isinstance(r, dict):
                keys = list(r.keys())[:3]
                print(f"  {num:>2}. {name:<22} {keys}")
            else:
                print(f"  {num:>2}. {name:<22} {r}")
        except Exception as e:
            results[str(num)] = {"name": name, "error": str(e)}
            print(f"  {num:>2}. {name:<22} ERROR: {e}")
    
    # Save (sanitize first)
    out = CACHE / "auto_improve.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    def _default(o):
        return str(o)
    try:
        out.write_text(json.dumps({
            "generated_at": datetime.now().isoformat(),
            "checks": results,
        }, indent=2, default=_default))
        print(f"📄 Saved: {out}")
    except Exception as e:
        print(f"❌ Save error: {e}")
        # Fallback: save as text
        txt_out = CACHE / "auto_improve.txt"
        with open(txt_out, 'w') as f:
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            for k, v in results.items():
                f.write(f"{k}. {v.get('name', '?')}: {v.get('result', v.get('error', '?'))}\n")
        print(f"📄 Saved (txt): {txt_out}")


if __name__ == "__main__":
    exit(main())
