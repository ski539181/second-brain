#!/usr/bin/env python3
"""
hll_stats.py - HyperLogLog-style unique counter (from dataset #6)

Counts unique items in fixed memory (~1.6% error, 4KB max).
Used for: unique tokens, unique topics, unique files touched per day.

Cost: 0.0001
"""
import re
import math
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"


def fnv1a_32(s: str) -> int:
    """FNV-1a 32-bit hash (from dataset #6)."""
    h = 0x811c9dc5
    for c in s.encode("utf-8"):
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def leading_zeros(x: int) -> int:
    """Count leading zeros in 32-bit int (ρ function from HLL)."""
    if not x:
        return 32
    c = 1
    while not (x & 0x80000000):
        c += 1
        x <<= 1
    return c


class HLL:
    """HyperLogLog for unique counting (m=4096, ±1.6% error)."""

    def __init__(self, b: int = 12):
        self.b = b
        self.m = 1 << b
        self.M = bytearray(self.m)

    def add(self, item: str):
        h = fnv1a_32(item)
        j = h >> (32 - self.b)
        w = (h << self.b) & 0xFFFFFFFF
        r = leading_zeros(w)
        if r > self.M[j]:
            self.M[j] = r

    def count(self) -> int:
        alpha = 0.7213 / (1 + 1.079 / self.m)
        raw = alpha * self.m * self.m / sum(2.0 ** -m for m in self.M)
        zeros = self.M.count(0)
        # Small range correction (Linear Counting)
        if raw <= 2.5 * self.m and zeros > 0:
            return round(self.m * math.log(self.m / zeros))
        return round(raw)

    def merge(self, other):
        result = HLL(self.b)
        for i in range(self.m):
            result.M[i] = max(self.M[i], other.M[i])
        return result


def tokenize(text: str) -> list:
    """Extract meaningful tokens (Thai + English)."""
    # English words
    en = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    # Thai words (best effort — split on whitespace + Thai punctuation)
    th = re.findall(r'[\u0E00-\u0E7F]{2,}', text)
    return en + th


def count_unique_in_note(note_path: Path, hll: HLL):
    """Add tokens from a note to HLL counter."""
    try:
        text = note_path.read_text(errors='ignore')
        for token in tokenize(text):
            hll.add(token)
    except Exception:
        pass


def daily_unique_stats(days: int = 1):
    """Count unique tokens across recent notes."""
    hll = HLL()
    note_count = 0
    char_count = 0
    cutoff = datetime.now() - timedelta(days=days)
    for md in NOTES.rglob("*.md"):
        try:
            if datetime.fromtimestamp(md.stat().st_mtime) < cutoff:
                continue
        except Exception:
            continue
        count_unique_in_note(md, hll)
        try:
            char_count += md.stat().st_size
        except Exception:
            pass
        note_count += 1
    return hll.count(), note_count, char_count


def main():
    print(f"📊 HLL Unique Counter — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    # Last 1, 7, 30 days
    for days in [1, 7, 30]:
        uniq, notes, chars = daily_unique_stats(days)
        print(f"  Last {days:>2}d: {uniq:>5} unique tokens | {notes:>3} notes | {chars/1024:.1f}KB")
    # Save snapshot
    cache = HERMES / "cache" / "hll_stats.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({
        "ts": datetime.now().isoformat(),
        "1d": daily_unique_stats(1)[0],
        "7d": daily_unique_stats(7)[0],
        "30d": daily_unique_stats(30)[0],
    }))
    print(f"\n💾 Saved: {cache}")


if __name__ == "__main__":
    main()
