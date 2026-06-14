#!/usr/bin/env python3
"""
headroom_lite.py - Minimal headroom-style compressor (no ML deps)

Inspired by chopratejas/headroom. Captures the 3 core concepts:
1. Compress — strip redundant text (whitespace, dup lines, boilerplate)
2. Cache — save full version locally for retrieval
3. Retrieve — return full on demand (CCR pattern)

Use: compress tool outputs before sending to LLM.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path

CACHE = Path.home() / ".hermes" / "cache" / "headroom_lite"
CACHE.mkdir(parents=True, exist_ok=True)


def compress(text: str, max_lines: int = 50) -> str:
    """Compress text by removing redundancy. Returns compressed + cache_id."""
    if not text:
        return text
    # Generate cache ID
    cache_id = hashlib.sha256(text.encode()).hexdigest()[:12]
    # Save full version
    (CACHE / f"{cache_id}.full.txt").write_text(text)
    # Compress
    lines = text.split("\n")
    seen = set()
    kept = []
    # Heuristics: keep lines with errors, key info; drop duplicates
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # Always keep lines with keywords
        important = any(kw in s.lower() for kw in [
            "error", "fail", "exception", "warning", "❌", "✅", "alert",
            "found", "match", "root:", "unique", "tests:", "test ",
            "memory:", "cron:", "github:", "disk:", "files:",
        ])
        # Deduplicate similar lines
        sig = s[:60]
        is_dup = sig in seen
        if important or not is_dup:
            seen.add(sig)
            kept.append(line)
        if len(kept) >= max_lines:
            kept.append(f"... [+{len(lines) - max_lines} more lines]")
            break
    out = "\n".join(kept)
    # Add retrieval hint
    if len(text) > len(out) * 1.5:
        out += f"\n\n💾 Full version: headroom_lite.py --retrieve {cache_id}"
    return out


def retrieve(cache_id: str) -> str:
    """Retrieve full version by cache_id."""
    f = CACHE / f"{cache_id}.full.txt"
    if f.exists():
        return f.read_text()
    return f"Not found: {cache_id}"


def stats() -> dict:
    """Compression stats."""
    files = list(CACHE.glob("*.full.txt"))
    total_full = sum(f.stat().st_size for f in files)
    return {
        "cached": len(files),
        "total_bytes": total_full,
        "cache_dir": str(CACHE),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  headroom_lite.py <file>           # compress file")
        print("  headroom_lite.py --retrieve <id>  # get full version")
        print("  headroom_lite.py --stats          # cache stats")
        return
    if sys.argv[1] == "--retrieve" and len(sys.argv) > 2:
        print(retrieve(sys.argv[2]))
    elif sys.argv[1] == "--stats":
        s = stats()
        print(f"📊 headroom_lite stats:")
        print(f"   Cached items: {s['cached']}")
        print(f"   Total bytes: {s['total_bytes']:,}")
        print(f"   Cache dir: {s['cache_dir']}")
    else:
        path = Path(sys.argv[1])
        if path.exists():
            text = path.read_text(errors="ignore")
            start = time.time()
            compressed = compress(text)
            elapsed = time.time() - start
            ratio = (1 - len(compressed) / max(len(text), 1)) * 100
            print(f"📊 Compression:")
            print(f"   Original: {len(text):,} chars / {text.count(chr(10))} lines")
            print(f"   Compressed: {len(compressed):,} chars / {compressed.count(chr(10))} lines")
            print(f"   Ratio: {ratio:.1f}% reduction")
            print(f"   Time: {elapsed*1000:.1f}ms")
            print()
            print("=== Compressed output ===")
            print(compressed)


if __name__ == "__main__":
    main()
