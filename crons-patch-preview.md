# Crons Patch Preview

> ✅ **Status: APPLIED 2026-06-13** — crons updated. Rollback: `~/.hermes/scripts/rollback_crons.sh` — Auto-Reasoning Integration

**Status:** PREPARED, NOT APPLIED — review + run `apply_cron_<id>.sh` to install

**Goal:** Make CEO Loop + Daily Review use `auto_reasoning.py` (real API param) for hard tasks, while keeping soft signal (output style) as fallback for simple ones.

**Why:** Currently both crons use only "🎚️ Effort Mode" soft signal (B). This adds optional real API param path (A) when needed.

## Safety
- Backup cron jobs.json before any change
- Rollback: `bash ~/.hermes/scripts/rollback_crons.sh`
- Per-cron opt-in: `use_real_reasoning: false` (default off)

---

## Cron #1: CEO Loop (`03862d9aeaac`)

### Change 1: Add pre-step to prompt

**Insert AFTER "🟢 ตื่นแล้ว" and BEFORE "📖 ดูแล้ว":**

```diff
 🟢 ตื่นแล้ว — [HH:MM] [DATE]
+🎚️ Effort (optional): ถ้า task ที่จะทำเป็น research/code/multi-step ให้ run ก่อน:
+   `python3 ~/.hermes/scripts/auto_reasoning.py "your working question here" --effort=high`
+   → ใช้ output นั้นเป็น foundation ต่อ
+   → ถ้า task เบาๆ (status check, summary) → skip pre-step
 📖 ดูแล้ว: Second Brain — [N], Kanban — [N], Loop ก่อนหน้า — [ผล]
```

### Change 2: Add config flag to jobs.json

```diff
 {
   "job_id": "03862d9aeaac",
   "name": "Autonomous CEO Loop",
+  "use_real_reasoning": false,  // opt-in
   "prompt": "..."
 }
```

**When `use_real_reasoning: true`:** cron will auto-prepend auto_reasoning.py call before processing the prompt.

---

## Cron #2: Daily Review (`0c76b7e0073c`)

### Change 1: Add pre-step to prompt

**Insert AFTER "🌙 Daily Review" header:**

```diff
 🌙 Daily Review — [DATE] (TH)
+🎚️ Effort (optional): ถ้าวันนี้มี ≥3 lessons ให้ summarize ด้วย:
+   `python3 ~/.hermes/scripts/auto_reasoning.py "summarize 3 lessons into 1 actionable insight" --effort=high`
 🎚️ Effort: medium
 📊 Score: [✅ X | ⚠️ Y | ❌ Z] / [N]
```

### Change 2: Same config flag pattern

```diff
 {
   "job_id": "0c76b7e0073c",
   "name": "Daily Review (20:00 TH)",
+  "use_real_reasoning": false,
   "prompt": "..."
 }
```

---

## How it would work end-to-end

### Scenario A: CEO Loop fires, finds complex task

1. Cron triggers
2. Hermes reads prompt → sees 🎚️ Effort pre-step
3. Decides: "this is research, use real reasoning"
4. Calls terminal: `python3 ~/.hermes/scripts/auto_reasoning.py "research X" --effort=high`
5. Gets detailed answer from M3 with reasoning_tokens=512
6. Continues with normal flow → outputs decision

### Scenario B: Simple task

1. Cron triggers
2. Hermes sees 🎚️ Effort step
3. Decides: "task is simple, skip pre-step"
4. Goes straight to decision
5. Outputs as before

### Scenario C: use_real_reasoning flag = true

1. Cron auto-runs pre-step (no decision needed)
2. Always uses high effort for foundation
3. More consistent but slower (49s+ for research)

---

## Risk assessment

| Risk | Level | Mitigation |
|---|---|---|
| Cron response time +30-50s | Medium | Optional pre-step, agent decides |
| Auto-detect picks wrong effort | Low | Can override with --effort=X |
| Cron fails if auto_reasoning.py errors | Low | Try/except in script |
| Affects existing cron output | Low | Additive only, format unchanged |
