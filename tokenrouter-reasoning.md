# [[TokenRouter]] + M3 — reasoning_effort support

**Status (verified 2026-06-13):** ✅ M3 รองรับ `reasoning_effort` ผ่าน TokenRouter API

## Setup
- **Base URL:** `https://api.tokenrouter.com/v1`
- **Model name:** `MiniMax-M3` (NO prefix `minimax/` — มี prefix = 503 model_not_found)
- **API format:** OpenAI-compatible
- **Key pool ใน `credential_pool`:** 2 unique keys
  - `sk-Ty6...n2Ae` (51 chars) — **VALID** → ใช้ได้, providers: `hermesai`, `hermess7`
  - `sk-saC...Xyux` (51 chars) — **INVALID** → 401, providers: `mytokenrouter`, `api.tokenrouter.com`, `hermes1`, `hermesx2`, `hermesx9`

## Request body
```json
{
  "model": "MiniMax-M3",
  "messages": [{"role": "user", "content": "..."}],
  "reasoning_effort": "none" | "low" | "medium" | "high"
}
```

## Verified results (4 prompts, 3 trials each)

| Effort | reasoning_tokens | time | quality |
|---|---|---|---|
| none | ~28-38 | 2-3s | short, terse |
| low | ~45 | 3s | brief Q&A |
| medium | ~42-275 | 5-12s | structured |
| high | ~35-512 | 6-49s | detailed, multi-section |

**Key insight:** effort ไม่แค่ "คิดเยอะ" แต่ "คิดดีกว่า" — response quality scale ชัดเจน (verified ด้วย 17*24, PG vs Mongo, Python debug)

## Tool: `auto_reasoning.py`
Path: `~/.[[Hermes]]/scripts/auto_reasoning.py`

**Features:**
- Heuristic detect effort จาก prompt (length + keywords LOW_KW/HIGH_KW)
- Auto-pick: none (<15 chars) / low (short) / medium (default) / high (research/code/analysis)
- Override: `--effort=high`
- Output: clean answer (strip ` tags) + stats (time, reasoning_tokens)
- JSON mode: `--json`

**Usage:**
```bash
python3 ~/.hermes/scripts/auto_reasoning.py "hi"
echo "research question" | python3 ~/.hermes/scripts/auto_reasoning.py
python3 ~/.hermes/scripts/auto_reasoning.py --effort=high "code question" --explain
```

## Notes
- Hermes default config DOES NOT forward `reasoning_effort` to API (run_agent.py logic)
- To use from Hermes: ต้อง patch run_agent.py หรือใช้ auto_reasoning.py แยก
- [[Cron]] prompts ตอนนี้ใช้ B (output style soft signal) — สามารถ upgrade เป็น A (real param) ผ่าน auto_reasoning.py
- 12s response time สำหรับ "hi" effort=none น่าจะเป็น cold start — math=17*24 effort=none = 3.2s
