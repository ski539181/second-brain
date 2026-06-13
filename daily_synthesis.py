#!/usr/bin/env python3
"""
daily_synthesis.py - Daily knowledge synthesis

Reads recent notes, finds common concepts, generates a synthesis
that surfaces connections not visible in any single note.

Two modes:
- Default: uses LLM (~500 tokens, ~$0.0001)
- --cheap: rule-based extraction, 0 tokens

Output: ~/.hermes/synthesis/{date}.md
"""
import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
SYNTHESIS_DIR = HERMES / "synthesis"
SYNTHESIS_DIR.mkdir(exist_ok=True)

CONCEPT_PATTERNS = {
    r"\b(cloudflare|CF)\b": "Cloudflare bypass",
    r"\b(tokenrouter|token router)\b": "TokenRouter usage",
    r"\b(tiktoken)\b": "Tiktoken tracking",
    r"\b(orchestrator)\b": "Orchestrator pattern",
    r"\b(scraper|scraping|ftscraper)\b": "Web scraping",
    r"\b(memory)\b": "Memory management",
    r"\b(cron|scheduler)\b": "Cron jobs",
    r"\b(skill|skills?)\b": "Skill system",
    r"\b(telegram)\b": "Telegram bot",
    r"\b(termux)\b": "Termux environment",
    r"\b(hermes)\b": "Hermes Agent",
    r"\b(curl_cffi|patchright|camoufox)\b": "Scraper libraries",
    r"\b(github|gh)\b": "GitHub integration",
    r"\b(obsidian|second brain|second-brain)\b": "Second Brain",
    r"\b(automation|automate)\b": "Automation",
    r"\b(metric|metrics)\b": "Metrics tracking",
    r"\b(reflection|reflect)\b": "Reflection practice",
    r"\b(practice|challenge)\b": "Coding challenges",
    r"\b(self.quiz|self.quiz|quiz)\b": "Self-quiz",
    r"\b(wikilink|wiki.?link)\b": "Note linking",
}


def get_recent_notes(days=7, limit=5):
    """Get most recently modified notes."""
    threshold = datetime.now() - timedelta(days=days)
    notes = []
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime > threshold:
                title_match = re.search(r"^#\s+(.+?)$", f.read_text(), re.MULTILINE)
                title = title_match.group(1).strip() if title_match else f.stem
                notes.append({
                    "file": f.name,
                    "title": title,
                    "mtime": mtime.isoformat(),
                    "size": f.stat().st_size,
                })
        except Exception:
            pass
    notes.sort(key=lambda x: x["mtime"], reverse=True)
    return notes[:limit]


def extract_concepts(text):
    """Extract concepts using regex patterns."""
    found = Counter()
    for pattern, concept in CONCEPT_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found[concept] = len(matches)
    return found


def find_common_concepts(notes_data, top_n=5):
    """Find concepts shared across recent notes."""
    all_concepts = Counter()
    for note in notes_data:
        try:
            text = (NOTES / note["file"]).read_text()
            concepts = extract_concepts(text)
            for c, n in concepts.items():
                all_concepts[c] += n
        except Exception:
            pass
    return all_concepts.most_common(top_n)


def rule_based_synthesis(notes_data, common_concepts):
    """Generate synthesis without LLM (rule-based)."""
    lines = []
    lines.append(f"# Daily Synthesis — {datetime.now().strftime('%Y-%m-%d')}\n")
    lines.append(f"**Notes analyzed:** {len(notes_data)} (last 7 days)\n")
    lines.append("\n## 📚 Notes in scope\n")
    for n in notes_data:
        lines.append(f"- **{n['title']}** (`{n['file']}`, {n['size']}b)")
    lines.append("\n## 🔗 Common concepts\n")
    if common_concepts:
        for c, n in common_concepts:
            bar = "█" * min(20, n) + "░" * (20 - min(20, n))
            lines.append(f"- **{c}** — {n} mentions {bar}")
    else:
        lines.append("- (no common concepts detected)")
    lines.append("\n## 💡 Connections\n")
    # Generate insight based on common concepts
    if common_concepts:
        top3 = [c for c, _ in common_concepts[:3]]
        if len(top3) >= 2:
            lines.append(f"Notes ในช่วง {len(notes_data)} วันที่ผ่านมามีการเชื่อมโยงระหว่าง **{top3[0]}** และ **{top3[1]}**")
            if len(top3) >= 3:
                lines.append(f"และ **{top3[2]}** — ทั้ง 3 หัวข้อนี้อาจเป็น cluster ใหญ่ที่ควรมี index note\n")
        lines.append("\n## 🎯 Suggested actions\n")
        for c, _ in common_concepts[:3]:
            slug = c.lower().replace(" ", "-")
            lines.append(f"- เพิ่ม `[[{c}]]` ใน notes ที่เกี่ยวข้อง (ถ้ามี)")
            lines.append(f"- สร้าง index note สำหรับ '{c}' ถ้ายังไม่มี")
    return "\n".join(lines)


def llm_synthesis(notes_data, common_concepts):
    """Use LLM for deeper synthesis. Requires curl + API access."""
    if not notes_data:
        return None
    # Read up to 3 notes (limit to 500 chars each for context)
    context = []
    for n in notes_data[:3]:
        try:
            text = (NOTES / n["file"]).read_text()
            context.append(f"## {n['title']}\n{text[:500]}")
        except Exception:
            pass
    prompt = f"""Synthesize the following notes (Thai OK, 2-3 sentences per note + 1 insight):

{chr(10).join(context)}

Focus on: connections between notes, surprising insights, actionable patterns.
Be concise. Output in Thai/English mix."""
    # Use TokenRouter API
    api_key_file = HERMES / "config" / "tokenrouter.key"
    if not api_key_file.exists():
        return None
    api_key = api_key_file.read_text().strip()
    try:
        result = subprocess.run([
            "curl", "-s", "-X", "POST",
            "https://api.tokenrouter.com/v1/chat/completions",
            "-H", "Authorization: Bearer " + api_key,
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "model": "MiniMax-M3",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
            }),
        ], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content
    except Exception as e:
        print(f"LLM error: {e}")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cheap", action="store_true", help="Rule-based only, 0 tokens")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    print(f"🧠 Daily Synthesis ({'cheap' if args.cheap else 'LLM'}) — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    notes = get_recent_notes(days=args.days, limit=args.limit)
    if not notes:
        print("No recent notes.")
        return 0
    common = find_common_concepts(notes)
    
    # Build output
    out = SYNTHESIS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    
    if args.cheap:
        body = rule_based_synthesis(notes, common)
    else:
        # Try LLM first, fall back to rule-based
        llm_result = llm_synthesis(notes, common)
        rule_result = rule_based_synthesis(notes, common)
        if llm_result:
            body = rule_result + "\n\n## 🤖 LLM Synthesis\n\n" + llm_result
        else:
            body = rule_result + "\n\n_(LLM unavailable, using rule-based only)_\n"
    
    out.write_text(body)
    print(f"📄 Saved: {out}")
    print(f"📚 Notes: {len(notes)} | Common concepts: {len(common)}")
    if common:
        print(f"   Top: {common[0][0]} ({common[0][1]} mentions)")
    return 0


if __name__ == "__main__":
    exit(main())
