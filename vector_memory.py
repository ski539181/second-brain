#!/usr/bin/env python3
"""
vector_memory.py - Semantic memory using TF-IDF (no model needed)

Pure Python implementation:
- Tokenize notes
- Compute TF-IDF vectors
- Cosine similarity for search

No downloads, no models, 0 dependencies.
"""
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
NOTES = HERMES / "notes"
CACHE = HERMES / "cache"
VECTOR_DIR = CACHE / "vector_memory"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

STOP_WORDS = set("""
a an the and or but if then else for to of in on at by with from
is are was were be been being have has had do does did will would could
should may might can this that these those it its they them their our your
i me my we us he she him her what which who whom how where when why
not no nor so than too very just also about above after again against
all am any as because before below between both did down during each few
for from further had has have having he her here hers herself him himself
his how itself just more most my myself now once only other our ours
ourselves out over own same she should some such than that the their
theirs them themselves then there these they this those through to too
under until up very was we were what when where which while who whom
why will with would you your yours yourself yourselves
""".split())


def tokenize(text):
    """Simple tokenizer."""
    text = text.lower()
    # Extract words (handles Thai by removing non-ASCII)
    words = re.findall(r"[a-z][a-z0-9_]+", text)
    # Filter stop words
    return [w for w in words if w not in STOP_WORDS and len(w) > 2]


def get_titles():
    """Load all notes."""
    titles = []
    for f in NOTES.rglob("*.md"):
        if "archive" in str(f):
            continue
        try:
            text = f.read_text()
            m = re.search(r"^#\s+(.+?)$", text, re.MULTILINE)
            title = m.group(1).strip() if m else f.stem
            titles.append((title, f, text))
        except Exception:
            pass
    return titles


def build_index():
    """Build TF-IDF index."""
    titles = get_titles()
    if not titles:
        return None

    print(f"📚 Indexing {len(titles)} notes...")

    # Tokenize all documents
    docs = []
    for title, fp, text in titles:
        tokens = tokenize(text)
        docs.append({
            "title": title,
            "file": fp.name,
            "tokens": tokens,
            "tf": Counter(tokens),
        })

    # Compute IDF
    df = Counter()
    for d in docs:
        for term in set(d["tokens"]):
            df[term] += 1

    n = len(docs)
    idf = {term: math.log((n + 1) / (df_t + 1)) + 1 for term, df_t in df.items()}

    # Compute TF-IDF vectors
    for d in docs:
        total = max(1, sum(d["tf"].values()))
        vec = {term: (count / total) * idf.get(term, 1)
               for term, count in d["tf"].items()}
        d["vec"] = vec
        d["norm"] = math.sqrt(sum(v * v for v in vec.values())) or 1.0

    # Save index
    index_data = {
        "generated_at": datetime.now().isoformat(),
        "n_docs": n,
        "vocab_size": len(idf),
        "docs": [
            {"title": d["title"], "file": d["file"], "vec": d["vec"]}
            for d in docs
        ],
    }
    (VECTOR_DIR / "tfidf_index.json").write_text(
        json.dumps(index_data, default=str)
    )
    return docs, idf


def load_index():
    """Load pre-computed index."""
    path = VECTOR_DIR / "tfidf_index.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def cosine(v1, v2):
    """Cosine similarity between two sparse vectors (dicts)."""
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    n1 = math.sqrt(sum(v * v for v in v1.values())) or 1.0
    n2 = math.sqrt(sum(v * v for v in v2.values())) or 1.0
    return dot / (n1 * n2)


def search(query, limit=5, index=None):
    """Search using TF-IDF + cosine similarity."""
    if index is None:
        index = load_index()
    if not index:
        return []

    # Tokenize query
    q_tokens = tokenize(query)
    if not q_tokens:
        return []
    q_tf = Counter(q_tokens)
    q_total = max(1, sum(q_tf.values()))
    q_vec = {t: (c / q_total) for t, c in q_tf.items()}

    # Score each doc
    results = []
    for d in index["docs"]:
        d_vec = d["vec"]
        # Compute query TF-IDF using index vocab
        # Get terms in both query and doc
        common = set(q_vec.keys()) & set(d_vec.keys())
        if not common:
            continue
        score = sum(q_vec[t] * d_vec[t] for t in common)
        if score > 0:
            results.append({
                "title": d["title"],
                "file": d["file"],
                "score": score,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def main():
    print(f"🧠 Vector Memory (TF-IDF) — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Build or update index
    result = build_index()
    if not result:
        print("❌ No notes to index")
        return 1
    docs, idf = result
    print(f"📊 Indexed: {len(docs)} notes, {len(idf)} unique terms\n")

    # Test queries
    index = load_index()
    test_queries = ["scraper", "memory", "cron", "skill", "improvement"]
    print("🔍 Test searches:")
    for q in test_queries:
        results = search(q, limit=3, index=index)
        print(f"  • '{q}': {len(results)} hits")
        for r in results[:2]:
            print(f"    - {r['title']} (score: {r['score']:.3f})")

    # Save stats
    stats = {
        "generated_at": datetime.now().isoformat(),
        "total_indexed": len(docs),
        "vocab_size": len(idf),
        "test_queries": test_queries,
    }
    (CACHE / "vector_stats.json").write_text(json.dumps(stats, indent=2))
    print(f"\n📄 Saved: vector_stats.json")
    return 0


if __name__ == "__main__":
    exit(main())
