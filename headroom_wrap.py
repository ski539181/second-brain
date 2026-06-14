#!/usr/bin/env python3
"""
headroom_wrap.py - Wrap headroom compression around LLM calls
- Auto-detect log/code/JSON content
- Compress before sending to LLM
- Save full version with retrieval hash
- Drop-in: use as llm_compress() before llm_call()
"""
import sys
import json
import time
from pathlib import Path
from typing import Any

CACHE = Path.home() / ".hermes" / "cache" / "headroom_full"
CACHE.mkdir(parents=True, exist_ok=True)

# Default model for token counting
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def llm_compress(messages: list, model: str = DEFAULT_MODEL, compress_user: bool = True) -> dict:
    """
    Compress messages for LLM call using headroom.

    Args:
        messages: OpenAI/Anthropic format [{"role": ..., "content": ...}]
        model: model name for token counting
        compress_user: whether to compress user messages (default True)

    Returns:
        {
            "messages": compressed_messages,
            "tokens_before": int,
            "tokens_after": int,
            "tokens_saved": int,
            "compression_ratio": float (0-1),
            "transforms": list,
            "cache_ids": list of retrieval hashes
        }
    """
    from headroom import compress
    start = time.time()
    result = compress(messages, model=model, compress_user_messages=compress_user)
    elapsed = time.time() - start
    # Save full version to cache for retrieval
    cache_ids = []
    for i, msg in enumerate(messages):
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 500:
            import hashlib
            cid = hashlib.sha256(content.encode()).hexdigest()[:16]
            (CACHE / f"{cid}.json").write_text(json.dumps({
                "role": msg.get("role"),
                "content": content,
                "original_tokens": result.tokens_before // max(len(messages), 1),
            }))
            cache_ids.append(cid)
    return {
        "messages": result.messages,
        "tokens_before": result.tokens_before,
        "tokens_after": result.tokens_after,
        "tokens_saved": result.tokens_saved,
        "compression_ratio": result.compression_ratio,
        "transforms": result.transforms_applied,
        "cache_ids": cache_ids,
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def retrieve(cache_id: str) -> str:
    """Retrieve full message content by cache_id."""
    f = CACHE / f"{cache_id}.json"
    if f.exists():
        return json.loads(f.read_text()).get("content", "")
    return f"Not found: {cache_id}"


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  headroom_wrap.py <file.json>   # compress messages from file")
        print("  headroom_wrap.py --retrieve <id>  # retrieve full")
        print("  headroom_wrap.py --demo        # run demo")
        return
    if sys.argv[1] == "--retrieve" and len(sys.argv) > 2:
        print(retrieve(sys.argv[2])[:2000])
    elif sys.argv[1] == "--demo":
        from headroom import compress
        # Real-world example: tool output (verbose)
        messages = [
            {"role": "user", "content": "Analyze this log:\n" + "\n".join(
                [f"DEBUG: processing item {i}" for i in range(300)] +
                [f"ERROR: failed item {i}" for i in range(3)]
            )},
        ]
        print("📥 Original message:", len(messages[0]["content"]), "chars")
        result = llm_compress(messages)
        print(f"📤 Compressed: {result['tokens_after']} tokens")
        print(f"💾 Saved: {result['tokens_saved']} tokens ({result['compression_ratio']*100:.1f}%)")
        print(f"⏱️  Time: {result['elapsed_ms']}ms")
        print(f"🔧 Transforms: {result['transforms']}")
        print()
        print("--- Compressed content ---")
        print(result["messages"][0]["content"][:500])
        if result["cache_ids"]:
            print(f"\n💾 Retrieve: headroom_wrap.py --retrieve {result['cache_ids'][0]}")
    else:
        # Compress from file
        f = Path(sys.argv[1])
        data = json.loads(f.read_text())
        result = llm_compress(data if isinstance(data, list) else data.get("messages", []))
        print(json.dumps({k: v for k, v in result.items() if k != "messages"}, indent=2))
        print("\nCompressed messages saved. Use --retrieve <id> to get full.")


if __name__ == "__main__":
    main()
