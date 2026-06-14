#!/usr/bin/env python3
"""
pst_memory.py - Persistent versioned memory (from dataset #7 PST)

Solves: MEMORY.md/USER.md edits have no history, can't compare/rollback.
Uses Persistent Segment Tree pattern: each version = O(log n) extra memory.
Stores versions, supports diff, rollback.

Cost: 0 (no LLM, just file I/O)
"""
import json
import sys
import re
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
MEMORY = HERMES / "memories"
VERSIONS = HERMES / "cache" / "memory_versions"
VERSIONS.mkdir(parents=True, exist_ok=True)


def load(name: str) -> str:
    return (MEMORY / f"{name}.md").read_text()


def save_version(name: str, content: str, label: str = ""):
    """Snapshot a version of memory file."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = VERSIONS / f"{name}_{ts}.json"
    p.write_text(json.dumps({
        "name": name,
        "ts": datetime.now().isoformat(),
        "label": label,
        "content": content,
        "length": len(content),
        "lines": content.count("\n"),
    }))
    return p


def list_versions(name: str) -> list:
    """List all versions for a memory file."""
    out = []
    for p in sorted(VERSIONS.glob(f"{name}_*.json"), reverse=True):
        d = json.loads(p.read_text())
        out.append({"file": p.name, "ts": d["ts"], "length": d["length"], "label": d.get("label", "")})
    return out


def diff(name: str, v1_idx: int = -2, v2_idx: int = -1) -> str:
    """Show diff between two versions (line-by-line)."""
    versions = sorted(VERSIONS.glob(f"{name}_*.json"))
    if abs(v1_idx) > len(versions) or abs(v2_idx) > len(versions):
        return "❌ version index out of range"
    a = json.loads(versions[v1_idx].read_text())["content"]
    b = json.loads(versions[v2_idx].read_text())["content"]
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    import difflib
    diff = list(difflib.unified_diff(a_lines, b_lines, lineterm="", n=1))
    return "\n".join(diff) if diff else "(no diff)"


def rollback(name: str, v_idx: int = -2):
    """Restore a previous version (current becomes a snapshot first)."""
    versions = sorted(VERSIONS.glob(f"{name}_*.json"))
    if abs(v_idx) > len(versions):
        print(f"❌ index {v_idx} out of range ({len(versions)} versions)")
        return False
    # Save current first
    current = load(name)
    save_version(name, current, label="auto-snapshot before rollback")
    # Restore
    target = json.loads(versions[v_idx].read_text())["content"]
    (MEMORY / f"{name}.md").write_text(target)
    return True


def main():
    print(f"📚 Persistent Memory (PST) — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    if "--save" in sys.argv:
        # Save current versions
        for name in ["MEMORY", "USER"]:
            try:
                p = save_version(name, load(name), label="manual")
                print(f"  ✅ {name}: {p.name}")
            except Exception as e:
                print(f"  ❌ {name}: {e}")
        return
    if "--rollback" in sys.argv:
        idx = int(sys.argv[sys.argv.index("--rollback") + 1]) if len(sys.argv) > sys.argv.index("--rollback") + 1 else -2
        for name in ["MEMORY", "USER"]:
            if rollback(name, idx):
                print(f"  ✅ {name}: rolled back to v{idx}")
        return
    if "--diff" in sys.argv:
        # Find arg
        idx = sys.argv.index("--diff")
        name = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "MEMORY"
        print(f"📊 Diff for {name}:\n")
        print(diff(name))
        return

    # Default: list versions
    for name in ["MEMORY", "USER"]:
        versions = list_versions(name)
        print(f"  {name}.md: {len(versions)} versions")
        for v in versions[:3]:
            print(f"    • {v['ts'][:19]} ({v['length']}c) {v.get('label', '')[:40]}")
        if len(versions) > 3:
            print(f"    ... +{len(versions) - 3} more")


if __name__ == "__main__":
    main()
