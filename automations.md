# Automations — 3 นาที shipped (2026-06-13)

## 3 New Automations

| Cron | Schedule | Script | Purpose |
|------|----------|--------|---------|
| `b4f84d4ccdf7` | ทุกชั่วโมง | `token_alarm.py` | Alert ถ้า cost > threshold |
| `2340b2a41c9f` | ทุก 30 นาที | `cron_health.py` | ตรวจ cron jobs ทำงานปกติ |
| `79e0163d825b` | อาทิตย์ละครั้ง | `auto_skill_create.py` | สร้าง skill auto |

## Features (vs 15-20 นาที version)

**Token alarm:**
- Daily + hourly thresholds (configurable via env)
- Trend detection (20% jump vs yesterday)
- EOD projection
- Dry-run mode

**Cron health:**
- Per-job interval parsing (cron expr + interval)
- Stale job detection (>2x expected interval)
- Failed status flagging
- Alert log for trends

**Auto-skill create:**
- Quality gate: 5+ occurrences
- Skip existing skills
- Dry-run mode
- Auto-generates SKILL.md with metadata

## Files
- `scripts/token_alarm.py` (4.6KB)
- `scripts/cron_health.py` (2.9KB)
- `scripts/auto_skill_create.py` (4.6KB)

## Total active crons
11 (was 9) — see notes/cron-manifest.md
