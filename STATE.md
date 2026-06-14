# Hermes State — Model Handoff Doc

> 📖 **อ่านอันนี้ก่อนเริ่ม** — ถ้าคุณเป็น model ใหม่ที่เพิ่งเข้ามา อ่านไฟล์นี้ก่อน 1 read = รู้ "ภาพรวม" ทันที
> ไฟล์นี้ถูก optimize ให้อ่านเร็ว + ใช้ token น้อย — bullet เป็นหลัก ไม่มี prose เยิ่นเย้อ

<!-- LAST_RUN: 04:30 2026-06-14 (TH) | Cron: 03862d9aeaac | Kanban: 0 active | Effort: low -->

---

## 👤 User Profile

- **Name:** Supakit Ketkaew
- **Channel:** Telegram (DM)
- **Timezone:** Asia/Bangkok (UTC+7) — ทุกเวลาใช้ Thailand time + 24h format (เช่น 15:50, ไม่ใช่ 3:50 PM)
- **Style:** terse + cute, kaomoji ok (ฅ^•ﻌ•^ฅ, ✨, 💕, 🐾)
- **Length:** ~3-4 short paragraphs (condense for simple topics)
- **Language:** ไทยหลัก + อังกฤษปน
- **Critical rules:**
  - ⚠️ Opt-in config changes (ห้าม auto-edit `~/.hermes/config.yaml` — รอ "ทำเลย")
  - ⚠️ Execute ไม่ delegate (run tools เอง, ห้ามส่ง curl command ให้ user)
  - ⚠️ ไม่ copy style จาก external content (ใช้ความรู้ ไม่ใช้รูปแบบ)

---

## 🔧 System

- **Hermes** (built-in Kanban = SQLite-backed)
- **Provider:** [[TokenRouter]] (custom OpenAI-compatible) — `https://api.tokenrouter.com/v1`
- **Cache:** ❌ ไม่ support `cache_control` (verified ใน `run_agent.py`) — ใช้ skills แทน
- **Local proxy:** `127.0.0.1:8400` (อาจไม่ listen — verify ก่อนใช้)
- **API key:** masked ในทุก output — ใช้ Hermes internal เท่านั้น

---

## ⏰ Active Cron Jobs

| Job ID | Name | Schedule | Purpose |
|---|---|---|---|
| `03862d9aeaac` | **CEO Loop** | ทุก 1 ชม. | ตื่น → อ่าน notes + Kanban → ตัดสินใจ → สร้าง task + ถาม feedback (✅/❌/🔇) |
| `0c76b7e0073c` | **Daily Review** | 20:00 TH (= 13:00 UTC) | score tasks → 1 บทเรียน → 1 ปรับปรุง → save to notes.md |

**Kanban status:** 0 tasks active (latest done: `t_4a703762` — refresh web-scraper-expert skill w/ 2025-26 findings, 2026-06-13 19:24 TH)

---

## 🧠 [[Memory]] Architecture

| Layer | Size | Injected? | Purpose |
|---|---|---|---|
| Main memory | ~2,200 chars | ✅ auto (ทุก turn) | Core preferences, pointer to notes |
| User profile | ~1,375 chars | ✅ auto (ทุก turn) | User style, rules, timezone |
| Extended notes | ไม่จำกัด | ❌ on-demand (grep) | Project context, decisions, gotchas |
| Skills | ไม่จำกัด | ✅ auto (on trigger) | Topic-specific knowledge |

**Cost tradeoff:** main/user auto = fast + small; notes/skills = bigger but on-demand/auto-trigger

---

## 📂 File Map (`~/.hermes/notes/`)

| File | Purpose | When to read |
|---|---|---|
| `README.md` | index + when to grep | new model boot |
| **`STATE.md`** | **handoff doc (อันนี้)** | new model boot |
| `notes.md` | Second Brain (projects, ideas, opportunities) | when topic matches |
| `scraper-cheatsheet.md` | quick formulas/patterns | scraper/Playwright/CF question |
| `scraper-antipatterns.md` | what NOT to do | scraper code review |
| `scraper-decision-tree.md` | when to do what | scraper problem-solving |
| `scraper-checklist.md` | pre-deploy verification | scraper deploy |
| `scraper-snippets.md` | copy-paste code | scraper implementation |
| `tokenrouter-reasoning.md` | M3 reasoning_effort API support (verified) | when prompt needs M3 effort tuning |

---

## 🎯 Active Skills

- **`web-scraper-expert`** — auto-load on: scraper, playwright, CF, circuit breaker, atomic write, stealth

---

## 🎯 Active Projects

1. **Web Scraper FT Dataset** (Claude Sonnet 4.6 generated)
   - Status: knowledge extracted → 1 skill + 5 reference files
   - Purpose: prep for fine-tuning (model ยังไม่ train)
   - Action: skill + 5 files = **temporary** (ลบเมื่อ FT เสร็จ)

2. **Autonomous CEO Loop**
   - Status: 2 cron jobs active + tested
   - Architecture: 1 hourly wake + 1 daily review

3. **Memory Efficiency**
   - Status: extended notes + skills-based memory (ไม่ใช้ cache)
   - Tradeoff: auto-injection vs on-demand (chose on-demand for capacity)

---

## 🔍 Quick Search Patterns

```bash
# User / setup
search_files pattern="Supakit|setup" path=~/.hermes/notes

# Provider / config
search_files pattern="TokenRouter|provider" path=~/.hermes/notes

# Cron / jobs
search_files pattern="cron|03862|0c76" path=~/.hermes/notes

# Web scraper
search_files pattern="scraper|playwright" path=~/.hermes/notes
# OR load skill:
skill_view name="web-scraper-expert"

# Past session work
session_search query="web scraper|CEO loop|cron"
```

---

## ⚠️ Gotchas (เจอแล้ว — กันพลาดซ้ำ)

1. **TokenRouter cache_control = no** (verified ใน code) — ใช้ skills-based memory แทน
2. **Local proxy อาจ down** (ไม่ listen port 8400) — verify ก่อน rely
3. **API key masked everywhere** — ดึงจาก Hermes internal เท่านั้น
4. **Cron output ใช้ format ที่ user เห็นชัด** — Thai + emoji + structured blocks
5. **User rejects verbose** — "งง" / "ตอบยาวเกิน" / "ตอบสั้นเกิน" เป็น feedback ทันที
6. **Config changes need explicit "ทำเลย"** — opt-in pattern สำคัญ
7. **M3 + reasoning_effort WORKS** (TokenRouter API) — ใช้ key `sk-Ty6...n2Ae`, model `MiniMax-M3` (no prefix), script `~/.hermes/scripts/auto_reasoning.py` — Key เก่า `sk-saC...Xyux` → 401

9. **Second Brain structure (2026-06-13):** /raw (read-only) + cross.md (rules) + podcast.md (sessions) + notes.md (knowledge) + STATE.md (state). Karpathy pattern (egBoq66lCRc).
8. **Hermes patched 2026-06-13** — `run_agent.py` + `chat_completions.py` มี `[PATCH hermes-reasoning]` markers 5+2 จุด — forward `reasoning_effort` to TokenRouter M3 — Backup: `run_agent.py.bak.20260613_115535`
9. **Config flag** `model.reasoning_effort: ""` (empty = default medium) — set to "none"/"low"/"medium"/"high" เพื่อ override
10. **Rollback scripts:** `~/.hermes/scripts/rollback_hermes_reasoning_patch.sh` + `rollback_crons.sh`

---

## 💡 Style for New Model

- **Read this file first** when starting a new session
- **Acknowledge** what you found (1-2 lines)
- **Don't repeat** the work shown here — build on it
- **Use grep** for project-specific questions
- **Use skills** for topic-specific knowledge
- **Ask before** modifying config, cron schedules, or creating new cron jobs
