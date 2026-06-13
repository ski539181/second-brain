#!/usr/bin/env python3
"""
effort_detect.py — Auto-detect effort level from message text.

Returns: "low" | "medium" | "high"

Heuristic (fast, no LLM):
- LOW keywords: quick, short, เร็วๆ, สั้นๆ, แค่, just, brief, tldr, 1 line
- HIGH keywords: research, analyze, compare, code, วิเคราะห์, เปรียบเทียบ, เขียน, design, debug
- Default: medium

Length boost:
- < 30 chars → low
- > 300 chars → +1 (low→med, med→high)

Usage:
  python3 effort_detect.py "your message here"
  # OR import
  from effort_detect import detect_effort
  detect_effort("write a function")
"""
import re
import sys

LOW_KEYWORDS = [
    r"\bquick\b", r"\bbrief\b", r"\bshort\b", r"\btldr\b", r"\bjust\b",
    r"เร็วๆ", r"สั้นๆ", r"แค่", r"แปปเดียว", r"ไม่ต้องยาว",
    r"\b1 line\b", r"\bone line\b", r"บรรทัดเดียว",
]

HIGH_KEYWORDS = [
    r"\bresearch\b", r"\banalyze\b", r"\banalysis\b", r"\bcompare\b",
    r"\bdesign\b", r"\bdebug\b", r"\bimplement\b", r"\bcode\b",
    r"\barchitecture\b", r"\brefactor\b", r"\boptimize\b",
    r"วิเคราะห์", r"เปรียบเทียบ", r"เขียน", r"ออกแบบ",
    r"ดีบั๊ก", r"ปรับปรุง", r"วิจัย", r"ศึกษา",
    r"ละเอียด", r"ครบถ้วน", r"ทั้งหมด",
]


def detect_effort(text: str) -> str:
    """Return 'low' | 'medium' | 'high' based on keyword + length heuristics."""
    if not text:
        return "medium"

    text_lower = text.lower()

    # Count keyword matches
    low_score = sum(1 for p in LOW_KEYWORDS if re.search(p, text_lower))
    high_score = sum(1 for p in HIGH_KEYWORDS if re.search(p, text_lower))

    # Length adjustment
    length = len(text)
    if length < 30:
        low_score += 1
    elif length > 300:
        high_score += 1

    # Decision
    if high_score > low_score:
        return "high"
    if low_score > high_score:
        return "low"
    return "medium"


# Effort behavior mapping
EFFORT_CONFIG = {
    "low": {
        "max_tokens": 500,
        "tool_budget": 2,
        "prompt_style": "terse",
        "thinking_hint": "1-2 bullets, ไม่ต้องยาว",
    },
    "medium": {
        "max_tokens": 2000,
        "tool_budget": 5,
        "prompt_style": "normal",
        "thinking_hint": "3-4 paragraphs, ปกติ",
    },
    "high": {
        "max_tokens": 4000,
        "tool_budget": 10,
        "prompt_style": "detailed",
        "thinking_hint": "คิดหลายมุม, ละเอียด, พิจารณา tradeoffs",
    },
}


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    effort = detect_effort(text)
    config = EFFORT_CONFIG[effort]
    print(f"effort: {effort}")
    print(f"max_tokens: {config['max_tokens']}")
    print(f"tool_budget: {config['tool_budget']}")
    print(f"style: {config['prompt_style']}")
