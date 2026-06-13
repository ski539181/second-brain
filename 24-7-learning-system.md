# 24/7 Learning System — Shipped 2026-06-13

## 3 Components

### 1. Practice Queue (`practice_queue.py`)
- Spaced repetition: failed → next time, mastered → 14 days
- Tracks mastery score per challenge (0-100)
- Picks next to practice based on priority

States: new → learning → reviewing → mastered

### 2. Reflection Journal (`reflection.py`)
- Auto-generates [[Daily]] journal entry
- Format: what I did, what worked, what failed, lessons, next actions
- Saved to `~/.[[Hermes]]/journal/{date}.md`

### 3. Metrics Dashboard (`metrics.py`)
- Aggregates: practice, journal, tokens, notes, [[Cron]], skills, scripts
- Overall learning score (0-100)
- Saved to `~/.hermes/cache/metrics.json`

## Cron Schedule

| Time | Job | Purpose |
|------|-----|---------|
| 09:00 daily | ed986765a0a9 | Update practice queue |
| 23:55 daily | 58096f91c62d | Generate reflection |
| */6 hours | 316ae53f335c | Refresh metrics |

## Initial Score: 32/100
- Practice mastery: 12.4%
- Pass rate: 31.1%
- Journal entries: 1
- Notes with wikilinks: 0/34

## Token Cost: 0 (Python only)

## Coverage
- 15/15 crons will run 24/7
- 3 new learning crons (was 15, now 18 active)
- Combined with existing 15 = 18 cron jobs
