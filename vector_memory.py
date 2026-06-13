#!/usr/bin/env python3
"""
vector_memory.py - Semantic memory using ChromaDB

Embeds all notes, enables semantic search across them.
Replaces flat JSON lookups with vector similarity.

Output: ~/.hermes/cache/vector_memory/
"""
import json
import re
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
VECTOR_DIR = CACHE / "vector_memory"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_OK = True
except Exception as e:
    CHROMA_OK = False
    CHROMA_ERR = str(e)


def get_titles():
    titles = []
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            text = f.read_text()
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            if m:
                titles.append((m.group(1).strip(), f, text[:2000]))
        except Exception:
            pass
    return titles


def build_index():
    """Build vector index from all notes."""
    if not CHROMA_OK:
        print(f"❌ ChromaDB not available: {CHROMA_ERR}")
        return None
    
    client = chromadb.PersistentClient(path=str(VECTOR_DIR))
    # Delete old collection if exists
    try:
        client.delete_collection("hermes_notes")
    except Exception:
        pass
    coll = client.create_collection("hermes_notes")
    
    titles = get_titles()
    if not titles:
        print("❌ No notes found")
        return None
    
    print(f"📚 Indexing {len(titles)} notes...")
    for i, (title, fp, text) in enumerate(titles):
        try:
            coll.add(
                ids=[f"note_{i}"],
                documents=[text],
                metadatas=[{"title": title, "file": fp.name}],
            )
        except Exception as e:
            print(f"  ⚠️ {fp.name}: {e}")
    
    return client, coll


def search(query, limit=5):
    """Semantic search across notes."""
    if not CHROMA_OK:
        return []
    if not query.strip():
        return []
    
    client = chromadb.PersistentClient(path=str(VECTOR_DIR))
    try:
        coll = client.get_collection("hermes_notes")
    except Exception:
        return []
    
    try:
        results = coll.query(query_texts=[query], n_results=limit)
        out = []
        for i in range(len(results["ids"][0])):
            out.append({
                "title": results["metadatas"][0][i].get("title", "?"),
                "file": results["metadatas"][0][i].get("file", "?"),
                "distance": results["distances"][0][i] if "distances" in results else None,
            })
        return out
    except Exception as e:
        print(f"Search error: {e}")
        return []


def main():
    print(f"🧠 Vector Memory — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    if not CHROMA_OK:
        print(f"❌ ChromaDB unavailable: {CHROMA_ERR}")
        return 1
    
    # Build or update index
    result = build_index()
    if not result:
        return 1
    client, coll = result
    
    # Test queries
    test_queries = ["scraper", "memory", "cron", "skill"]
    print(f"\n🔍 Test searches:")
    for q in test_queries:
        results = search(q, limit=3)
        print(f"  • '{q}': {len(results)} hits")
        for r in results[:2]:
            print(f"    - {r['title']} ({r.get('distance', '?')})")
    
    # Save index stats
    count = coll.count()
    stats = {
        "generated_at": datetime.now().isoformat(),
        "total_indexed": count,
        "test_queries": test_queries,
    }
    (CACHE / "vector_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"\n📄 Indexed: {count} notes")
    return 0


if __name__ == "__main__":
    exit(main())
