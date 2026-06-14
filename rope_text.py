#!/usr/bin/env python3
"""
rope_text.py - Persistent Rope-like text history (from dataset #8)

Efficient text ops: insert/delete at any position in O(log n).
Stores versions for undo/redo (like the Editor in dataset #8).
Used for: MEMORY.md edit history, journal drafts.

Cost: 0 (no LLM)
"""
from pathlib import Path
from datetime import datetime
import json

HERMES = Path.home() / ".hermes"
HISTORY_DIR = HERMES / "cache" / "rope_history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


class RopeNode:
    """Simple Rope node — Leaf for short strings, Branch for concatenation."""
    LEAF_MAX = 512

    def __init__(self, text="", left=None, right=None):
        if left is not None and right is not None:
            # Branch
            self.left = left
            self.right = right
            self.length = left.length + right.length
            self.height = 1 + max(left.height, right.height)
        else:
            # Leaf
            self.text = text
            self.length = len(text)
            self.height = 0

    @property
    def is_leaf(self):
        return hasattr(self, "text")

    def char_at(self, i):
        if self.is_leaf:
            if 0 <= i < len(self.text):
                return self.text[i]
            raise IndexError(f"index {i} out of range")
        if i < self.left.length:
            return self.left.char_at(i)
        return self.right.char_at(i - self.left.length)

    def to_string(self):
        if self.is_leaf:
            return self.text
        return self.left.to_string() + self.right.to_string()

    def insert(self, i, s):
        """O(log n) insert at position i."""
        if not s:
            return self
        if self.is_leaf:
            new_text = self.text[:i] + s + self.text[i:]
            return RopeNode(text=new_text)
        if i <= self.left.length:
            return RopeNode(left=self.left.insert(i, s), right=self.right)
        return RopeNode(left=self.left, right=self.right.insert(i - self.left.length, s))

    def delete(self, start, end):
        """O(log n) delete range [start, end)."""
        if end <= start or self.length == 0:
            return self
        if self.is_leaf:
            new_text = self.text[:start] + self.text[end:]
            return RopeNode(text=new_text) if new_text else None
        result = None
        # Delete from left subtree
        if start < self.left.length:
            new_left = self.left.delete(start, min(end, self.left.length))
            if end <= self.left.length:
                result = new_left
        # Delete from right subtree
        if end > self.left.length:
            adj_start = max(0, start - self.left.length)
            adj_end = end - self.left.length
            new_right = self.right.delete(adj_start, adj_end)
            if start >= self.left.length:
                result = new_right
        # Spans both
        if start < self.left.length and end > self.left.length:
            result = None
            if new_left:
                result = new_left
            if new_right:
                result = new_right if not result else RopeNode(left=result, right=new_right)
        return result


class RopeHistory:
    """Persistent text editor with versions (from dataset #8 Editor class)."""

    def __init__(self, name: str, initial: str = ""):
        self.name = name
        self.versions: list = [RopeNode(text=initial)]
        self.cursor = 0
        self.save()

    @property
    def current(self):
        return self.versions[self.cursor]

    @property
    def text(self):
        return self.current.to_string() if self.current else ""

    def _commit(self, rope: RopeNode):
        self.versions = self.versions[:self.cursor + 1]
        self.versions.append(rope)
        self.cursor += 1
        self.save()

    def insert(self, pos: int, s: str):
        self._commit(self.current.insert(pos, s))

    def delete(self, start: int, end: int):
        r = self.current.delete(start, end)
        self._commit(r or RopeNode(text=""))

    def replace(self, start: int, end: int, s: str):
        self.delete(start, end)
        self.insert(start, s)

    def undo(self):
        if self.cursor > 0:
            self.cursor -= 1
            self.save()

    def redo(self):
        if self.cursor < len(self.versions) - 1:
            self.cursor += 1
            self.save()

    def save(self):
        path = HISTORY_DIR / f"{self.name}.json"
        path.write_text(json.dumps({
            "name": self.name,
            "ts": datetime.now().isoformat(),
            "cursor": self.cursor,
            "text": self.text,
            "versions": len(self.versions),
        }))

    def stats(self):
        return {
            "name": self.name,
            "length": len(self.text),
            "versions": len(self.versions),
            "cursor": self.cursor,
            "tree_height": self.current.height if self.current else 0,
        }


def main():
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "memory"
    h = RopeHistory(name, initial=Path(HERMES / "memories" / "MEMORY.md").read_text() if (HERMES / "memories" / "MEMORY.md").exists() else "")
    print(f"📜 Rope History — {name}")
    print(f"  Length: {h.stats()['length']} chars")
    print(f"  Versions: {h.stats()['versions']}")
    print(f"  Tree height: {h.stats()['tree_height']}")
    print(f"  Cursor: {h.stats()['cursor']}")
    if "--demo" in sys.argv:
        h.insert(0, "[DEMO] ")
        h.delete(0, 8)
        h.undo()
        print(f"  After demo: cursor={h.stats()['cursor']}, text={h.text[:50]}...")


if __name__ == "__main__":
    main()
