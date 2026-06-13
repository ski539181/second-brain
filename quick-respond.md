# Quick Respond — LLM Bypass (2026-06-13)

## What
Bypass LLM for mechanical queries (time, [[Memory]], [[Cron]], etc.). Speed: 100-300x.

## Files
- `scripts/quick_respond.py` (5.1KB) — Python bypass for 8 query types
- `scripts/quick_cache.py` (2.8KB) — pre-computed cache (refreshed every 5 min)
- `skills/quick-respond/[[Skill]].md` (3KB) — LLM trigger guide
- `cron: 2dcf7323f555` — refreshes cache every 5 minutes

## Usage (from LLM)
```bash
python3 ~/.hermes/scripts/quick_respond.py "<query>"
# Returns: "⚡ BYPASS: <answer>" or "LLM_REQUIRED"
```

## Cache
- File: `~/.hermes/cache/quick-stats.json`
- Refreshed: every 5 min
- Fields: memory, disk, kanban, cron, commits, notes_count

## Token cost
0 for bypassed queries (Python only).
