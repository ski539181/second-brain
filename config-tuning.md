# [[Hermes]] Config Tuning (2026-06-12 session)

## Context window optimization
- `tool_output.max_bytes: 20000` — limit tool output to 20KB
- `tool_output.max_lines: 500` — limit lines
- `tool_output.max_line_length: 1000` — limit line width
- `compression.threshold: 0.4` — start compression at 40% capacity
- `compression.engine: compressor` — LLM-based compression

## [[Memory]] limits (2026-06-13 update)
- `memory_char_limit: 3000` (was 2200, +36%)
- `user_char_limit: 1800` (was 1375, +31%)
- Reason: original limits caused auto-curation to be too aggressive

## User preferences
- Agrees with **conservative tuning** (smaller cuts) over aggressive optimization
- Watches for memory bloat (asked specifically how to prevent filling up)

## Cost mitigation
1. Compression engine uses cheap model
2. Tool output truncated
3. Lazy-load notes via pointer (don't auto-inject)
4. Periodic auto-cleanup ([[Cron]] moves old entries to notes)
