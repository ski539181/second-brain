# Active Cron Jobs (2026-06-13)

| Job ID | Name | Schedule | Purpose |
|--------|------|----------|---------|
| `03862d9aeaac` | Autonomous CEO Loop | hourly | Kanban autopilot, priority picking |
| `0c76b7e0073c` | Daily Review | 20:00 TH daily | Output priority, FT pipeline status |
| `1a1625e5c335` | Obsidian Brain Reminder | 2026-06-14 12:00 | One-shot: remind to set up Obsidian on PC |
| `ef71fb37aaa3` | Auto-cleanup memory | Sun 3:00 AM | Move old memory entries to archive |
| `5c524b948496` | Orchestrator sync | Daily 4:00 AM | Cross-system sync (dedup, pointers, archive, patterns) |

## Where to manage

- List: `hermes cron list` (CLI)
- Output logs: `~/.hermes/cron/output/<job_id>/`
- Job definitions: `~/.hermes/cron/jobs.json`

## Token cost per cron

- CEO Loop: 1 LLM call/hour (orchestrator pick)
- Daily Review: 1 LLM call/day
- Memory cleanup: 0 LLM (Python only)
- Orchestrator: 0 LLM (Python only)
- Obsidian reminder: 1 LLM call (one-shot)

Total: ~26 LLM calls/day (mostly routine)
