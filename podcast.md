# podcast.md — Session Summary Log

> **Purpose:** สรุป session ย่อ — ประหยัด token ตอนอ่านซ้ำ
> เขียนทุก session ที่มีงานสำคัญ (Karpathy pattern, [15:03] [15:44])
> **Format:** 5-10 bullets + outcomes + lessons

---

## 📅 2026-06-13 (TH) — Session 21:00

**🎯 Focus:** Verify all systems + apply Karpathy 17 insights

**📋 What happened:**
- ทดสอบ 10 ระบบ → เจอ 5 weak points (config flag, rollback untested, no monitoring, etc.)
- Config flag = empty (set `low` ใหม่) ✅
- 223s anomaly = ปกติ (65-130s hermes chat) — ไม่ใช่ bug
- สร้าง `reapply_hermes_reasoning.sh` (กัน Hermes update)
- สร้าง `monitor_cron_effort.py` (track effort usage)
- สร้าง `~/.hermes/notes/ai-knowledge.md` (10 insights จาก Karpathy 17)
- Memory update: pointer → `notes/ai-knowledge.md`
- Crons updated: เพิ่ม Quality Rules (verify facts, specific, iterate)

**🆕 Artifacts (5):**
1. `reapply_hermes_reasoning.sh` (1458 bytes)
2. `monitor_cron_effort.py` (1747 bytes)
3. `notes/ai-knowledge.md` (5979 bytes) — 10 insights
4. Crons: CEO Loop 4483→4866, Daily Review 1742→2125
5. Second Brain structure: /raw, cross.md, podcast.md

**📚 Lessons:**
- wall-clock hermes = 65-130s (overhead ใหญ่กว่า M3 portion)
- low effort ประหยัด ~2-3s (จาก M3) + token cost
- Memory 100% → ใช้ notes/ แทน
- Display masks แต่ file เก็บจริง — ระวังตอน edit

**🔗 References:**
- 17 YouTube IDs: `notes/ai-knowledge.md`
- System state: `notes/STATE.md`
- Feedback: `notes/cron-decisions.md`

---

## 📅 2026-06-13 (TH) — Session 13:00

**🎯 Focus:** Apply Hermes patch + update crons (M3 reasoning_effort)

**📋 What happened:**
- สร้าง `auto_reasoning.py` (4.8KB) — auto-detect + call M3
- Patch Hermes 7 จุด (5 run_agent.py + 2 chat_completions.py)
- Test 10 cases → 9/10 auto-detect ถูก, 10/10 ตอบถูก
- Config flag `model.reasoning_effort` เพิ่ม
- Crons updated (CEO + Daily Review)
- End-to-end: M3 ตอบ "OK from M3", 25*4=100, 8*7=56

**🆕 Artifacts (5):**
1. `auto_reasoning.py`
2. `rollback_hermes_reasoning_patch.sh` (908B)
3. `rollback_crons.sh` (662B)
4. `notes/hermes-patch-preview.md` (4.2KB)
5. `notes/crons-patch-preview.md` (3.4KB)

**📚 Lessons:**
- M3 รองรับ `reasoning_effort` (4 values) — verified
- Key เก่า (sk-saC...) = 401, Key ใหม่ (sk-Ty6...) = works
- Model name = `MiniMax-M3` (no prefix)
- Display mask ≠ file content (api_key ดูสั้นแต่จริงยาว)

---

## 📅 2026-06-13 (TH) — Session 09:00 (CEO Loop t_4a01680b)

**🎯 Focus:** CF bypass research for web scraper

**📋 What happened:**
- Research CF bypass tools (2025-26)
- Verdict: `patchright-nodejs` = drop-in fix ≤1 ชม.
- Brief 5.8KB ใน `notes.md`
- Refreshed `web-scraper-expert` skill
- เพิ่ม Migration Checklist 5 steps

**📚 Lessons:**
- 2023-era stealth patches ตายแล้ว
- patchright (713★) = primary recommendation
- camoufox (9.2k★) = alternative
- FlareSolverr (14.3k★) = last resort

---

## 📅 2026-06-12 — Earlier session (Karpathy 17 analysis)

**🎯 Focus:** Analyze 17 Karpathy videos

**📋 What happened:**
- Fetched 17 YouTube titles/channels (parallel)
- All from Andrej Karpathy
- Categories: SD dreams, backprop, makemore, GPT, LLM intro

**🆕 Artifacts:**
- (รอ integrate ลง notes)

**📚 Lessons:**
- 10 actionable insights for LLM users
- (Details ใน `notes/ai-knowledge.md`)

---

## 💡 How to use this file

1. **Start of session** → อ่าน podcast.md ก่อน
2. **ถ้าเจอ relevant** → load full notes.md
3. **ถ้าไม่เจอ** → continue normally
4. **End of session** → append entry ใหม่ (5-10 bullets)

**Target:** ลด token 50% เมื่อ recall past sessions


## 📅 2026-06-13 (TH) — Session 21:30 (Second Brain setup)

**🎯 Focus:** Apply Karpathy Second Brain pattern (egBoq66lCRc) + use it immediately

**📋 What happened:**
- Verified video egBoq66lCRc — "ทำตาม Andrej Karpathy — AI เก่งขึ้น x10!"
- Compared with current `~/.hermes/notes/` — already follows pattern (3 of 6 files)
- Created 3 missing pieces: `/raw/`, `cross.md`, `podcast.md`
- **USED IT NOW:** ingested karpathy-second-brain raw → processed to notes.md (Second Brain section)
- Updated README.md (4 entries) + STATE.md (rule #9)
- Memory at 98% → used notes instead

**🆕 Artifacts (3):**
1. `raw/2026-06-13_karpathy-second-brain.md` (6.8KB) — raw input
2. `cross.md` (3.7KB) — AI rules (workflow + safety)
3. `podcast.md` (4.1KB) — session summaries (5 entries now)

**🧹 Cleanup:**
- Discovered `config-effort-patch.md` (1.5KB) — obsolete (M3 DOES support reasoning_effort, was wrong before)
- 3 patch preview files (hermes/crons) — can archive (work done)

**📚 Lessons:**
- User's existing structure = already 50% Karpathy-compliant
- Adding 3 files = full compliance
- Cross.md rules = working (followed workflow correctly)
- "ใช้เลย" = use immediately, don't wait

**🔗 Cross-refs:**
- raw input → notes.md (Second Brain section)
- cross.md (rules) → followed
- podcast.md (this entry)
