# Skills Index (2026-06-13)

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `orchestrator` | Cross-system sync (memory/notes/kanban/cron/skills) | "silo", "sync", "consolidate" |
| `speed-toolbox` | 30x speedup via PTC + parallel + bash pipeline | "เร็ว", "faster", "speedup" |
| `hermes-context-management` | Context window tuning | "memory too big", "running out of tokens" |
| `hermes-provider-configuration` | Provider/model config errors | "Unknown provider" |
| `hermes-config-safety` | Iron rules for editing config.yaml | before any config edit |
| `second-brain` | Karpathy-style 6-brain notes system | "second brain", "graph" |
| `web-scraper-expert` | Production web scraper | "scrape", "crawler", "playwright" |
| `working-with-llm-generated-content` | Use Claude/GPT output as reference | "FT data", "AI-generated" |
| `autonomous-agent-loop` | Self-driving agent cron loops | "autonomous", "loop" |
| `knowledge-adoption` | Adopt knowledge from user-shared content | "paste this", "reference" |
| `user-communication-style` | Capture user style | "style", "communication" |

## When to load which
- **User says "เร็ว" / "faster"** → `speed-toolbox` (this skill)
- **Memory at 70%+** → `hermes-context-management`
- **Cron job fails** → `orchestrator` + check kanban
- **Config error** → `hermes-config-safety` first
