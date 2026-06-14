#!/usr/bin/env python3
"""
memory_auto_manage.py - Self-managing memory
- Auto-bump caps when full (no user action)
- Auto-compress old/duplicate entries
- Silent operation
- Max 2x cap (safety)

Cron: 0 */6 * * * (every 6h)
"""
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
CONFIG = HERMES / "config.yaml"
MEMORY = HERMES / "memories" / "MEMORY.md"
USER = HERMES / "memories" / "USER.md"
CACHE = HERMES / "cache" / "memory_manage.json"

# Current + max caps
LIMITS = {
    "memory_char_limit": {"current": 4500, "max": 6000, "default": 3000},
    "user_char_limit": {"current": 2700, "max": 3600, "default": 1800},
}
SOURCES = {
    "memory_char_limit": MEMORY,
    "user_char_limit": USER,
}

# Thresholds
COMPRESS_THRESHOLD = 85  # % — try compress first
BUMP_THRESHOLD = 95      # % — auto-bump if still tight


def get_pct():
    result = {}
    for key, info in LIMITS.items():
        path = SOURCES[key]
        if path.exists():
            size = len(path.read_text())
            result[key] = {
                "size": size,
                "limit": info["current"],
                "pct": size / info["current"] * 100,
            }
    return result


def bump_cap(key):
    """Bump the cap in config.yaml by 1.2x (capped at max)."""
    info = LIMITS[key]
    new_cap = min(int(info["current"] * 1.2), info["max"])
    if new_cap <= info["current"]:
        return False, "at max"

    content = CONFIG.read_text()
    pattern = rf"^{key}:\s*\d+"
    new_content = re.sub(pattern, f"{key}: {new_cap}", content, flags=re.MULTILINE)
    if new_content != content:
        CONFIG.write_text(new_content)
        info["current"] = new_cap
        return True, f"{info['current']//int(1.2)} → {new_cap}"
    return False, "config not updated"


def compress_old():
    """Remove oldest/lowest-priority entries from MEMORY/USER."""
    actions = []
    for path in [MEMORY, USER]:
        if not path.exists():
            continue
        text = path.read_text()
        # Split by §
        entries = [e.strip() for e in text.split("§") if e.strip()]
        if len(entries) <= 3:
            continue
        # Keep first 60% (assume top = important)
        keep = int(len(entries) * 0.7)
        # Archive removed
        archive_dir = HERMES / "notes" / "archive" / "memory"
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = archive_dir / f"{path.stem}_{ts}.md"
        archive_file.write_text("\n\n§\n".join(entries[keep:]))
        # Rewrite
        path.write_text("§\n" + "\n\n§\n".join(entries[:keep]) + "\n")
        actions.append(f"{path.stem}: {len(entries)} → {keep}")
    return actions


def main():
    stats = get_pct()
    log = {"ran_at": datetime.now().isoformat(), "actions": []}

    for key, s in stats.items():
        if s["pct"] >= BUMP_THRESHOLD:
            # Auto-bump
            ok, msg = bump_cap(key)
            if ok:
                log["actions"].append(f"🔼 {key}: {msg} (was {s['pct']:.0f}%)")
        elif s["pct"] >= COMPRESS_THRESHOLD:
            # Try compress first
            actions = compress_old()
            for a in actions:
                log["actions"].append(f"🗜️ {a}")
            # Recheck
            new_stats = get_pct()
            if new_stats[key]["pct"] >= BUMP_THRESHOLD:
                ok, msg = bump_cap(key)
                if ok:
                    log["actions"].append(f"🔼 {key} (after compress): {msg}")

    # Save log
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if CACHE.exists():
        try:
            existing = json.loads(CACHE.read_text())
        except Exception:
            existing = []
    existing.append(log)
    CACHE.write_text(json.dumps(existing[-20:], indent=2))

    # Print status
    print("📊 Memory health:")
    for key, s in get_pct().items():
        bar_len = int(s["pct"] / 5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"  {key.replace('_char_limit', ''):6} {bar} {s['pct']:.0f}% ({s['size']}/{s['limit']})")
    if log["actions"]:
        print("\n🔧 Auto actions:")
        for a in log["actions"]:
            print(f"  {a}")


if __name__ == "__main__":
    main()
