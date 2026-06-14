#!/usr/bin/env python3
"""
merkle_notes.py - Note integrity via Merkle tree (from dataset #5)

Hashes all notes → builds Merkle tree → saves root.
Verify: re-hash → compare root → detect tampering.
Useful for: cron checks note integrity, detect edits outside Hermes.

Cost: 0 (just SHA256)
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
ROOT_FILE = CACHE / "merkle_root.json"


def H(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path) -> str:
    """Hash file content + mtime for change detection."""
    try:
        content = path.read_bytes()
        mtime = str(path.stat().st_mtime).encode()
        return H(content + mtime)
    except Exception:
        return ""


def build_tree(hashes: list) -> list:
    """Build Merkle tree from leaf hashes, return all levels (bottom-up)."""
    if not hashes:
        return [[H(b"")]]
    # Pad to power of 2
    while len(hashes) & (len(hashes) - 1):
        hashes.append(hashes[-1])
    tree = [hashes[:]]
    level = hashes[:]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            next_level.append(H((level[i] + level[i + 1]).encode()))
        tree.append(next_level)
        level = next_level
    return tree


def merkle_root() -> str:
    """Build Merkle root over all notes + scripts."""
    files = []
    # Hash all notes
    for md in sorted(NOTES.rglob("*.md")):
        if ".git" in md.parts:
            continue
        files.append(("note", str(md.relative_to(HERMES)), hash_file(md)))
    # Hash all scripts
    scripts = HERMES / "scripts"
    for py in sorted(scripts.glob("*.py")):
        files.append(("script", py.name, hash_file(py)))
    # Build tree
    hashes = [f[2] for f in files]
    tree = build_tree(hashes)
    return tree[-1][0], tree, files


def verify() -> bool:
    """Verify current state matches saved root."""
    if not ROOT_FILE.exists():
        return False, "no saved root"
    saved_root = json.loads(ROOT_FILE.read_text())["root"]
    current_root, _, _ = merkle_root()
    return current_root == saved_root, current_root


def main():
    print(f"🌳 Merkle Note Integrity — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    root, tree, files = merkle_root()
    print(f"  Files: {len(files)} (notes + scripts)")
    print(f"  Tree height: {len(tree)}")
    print(f"  Root: {root[:16]}...{root[-8:]}")

    if "--save" in sys.argv:
        ROOT_FILE.parent.mkdir(parents=True, exist_ok=True)
        ROOT_FILE.write_text(json.dumps({
            "ts": datetime.now().isoformat(),
            "root": root,
            "files": len(files),
        }, indent=2))
        print(f"\n💾 Saved: {ROOT_FILE}")
    elif "--verify" in sys.argv:
        ok, current = verify()
        if ok:
            print(f"\n✅ Integrity OK")
        elif current == "no saved root":
            print(f"\n⚠️  No baseline (run with --save first)")
        else:
            print(f"\n❌ TAMPERING DETECTED")
            print(f"  Saved:   {ROOT_FILE.read_text()[:80]}")
            print(f"  Current: {current[:80]}")
    else:
        ok, current = verify()
        if not ok and current != "no saved root":
            print(f"\n⚠️  Changes detected since last save")


if __name__ == "__main__":
    main()
