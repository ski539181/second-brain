---
name: vol2-auto-consult
description: Auto-consult vol2 dataset for system design topics. Triggers on keywords like raft, lsm, merkle, consensus, lock-free, neural, hyperloglog, persistent, rope, dns, two-phase, actor, distributed.
---

# vol2 Auto-Consult [[Skill]]

When user asks about system-level design topics covered by vol2, **automatically** consult `vol2_index.py` BEFORE responding.

## Trigger Topics
- **Consensus:** raft, paxos, leader election, log replication
- **Storage:** lsm, sstable, memtable, wal, compaction
- **Lock-free:** cas, mpsc, spsc, atomic, treiber, aba
- **ML:** neural, autograd, adam, backprop, xor
- **Integrity:** merkle, sparse merkle, inclusion proof
- **Counting:** hyperloglog, cardinality, distinct count
- **Persistent DS:** persistent, versioning, segment tree, kth smallest
- **Text:** rope, persistent editor, undo, redo
- **Network:** dns, resolver, wire format
- **Locking:** two-phase, deadlock, wait-for
- **Concurrency:** actor, mailbox, supervision, fault tolerance

## Workflow

1. **Detect** topic in user query (Thai/English keywords)
2. **Run** `python3 /root/.[[Hermes]]/scripts/vol2_index.py <topic>` (summary only — NOT `--full`)
3. **Check** bug flag (🐛 = caution, ✅ = safe)
4. **Apply** pattern/concept only — NEVER copy code directly
5. **If bug-flagged** topic: explicitly tell user the known bug, extract pattern, write fresh code

## Rules

- ❌ Never paste vol2 code directly (6 entries have bugs)
- ❌ Never use `--full` flag (waste context)
- ✅ Use summary + Thinking & Logic patterns
- ✅ Mention vol2 reference briefly (e.g., "อ้างอิง vol2 entry 005")
- ✅ Check `KNOWN_BUGS` and warn if relevant
- ✅ Combine with my own knowledge (vol2 = reference, not source of truth)

## Quick Lookup

```bash
# See all topics
python3 /root/.hermes/scripts/vol2_index.py

# Look up specific topic (safe mode — summary only)
python3 /root/.hermes/scripts/vol2_index.py raft
python3 /root/.hermes/scripts/vol2_index.py merkle
python3 /root/.hermes/scripts/vol2_index.py hyperloglog
```

## Integration

- Script: `~/.hermes/scripts/vol2_index.py`
- Index: `~/.hermes/cache/vol2_index.json` (rebuild with `--rebuild`)
- Tested: A/B test showed vol2 concepts help in-context (+25% on conceptual Qs)
- Don't add to [[Cron]] (lookup is on-demand only — no auto-spam)

## Result Format (in response)

When applying vol2 knowledge:
```
💡 อ้างอิง vol2 entry 00X — <topic>
- Pattern: <extracted concept>
- Known issues: <bug warning if any>
- My approach: <how I'll implement>
```
