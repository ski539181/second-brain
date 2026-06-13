# Config Patch — Effort Switching (รอ approve)
> ⚠️ ไฟล์นี้เป็น "patch" ไม่ได้ apply แล้ว
> ดู diff แล้วบอก "ทำเลย" ถ้าโอเค → ผม apply ให้

## Diff (จะเพิ่มใน `~/.hermes/config.yaml`)

```yaml
# เพิ่มต่อท้าย section 'agent:' (หรือสร้าง section ใหม่)
agent:
  # ... existing settings ...
  effort:
    enabled: true
    default: medium          # low | medium | high
    auto_detect: true        # ใช้ heuristic จาก message
    levels:
      low:
        max_tokens: 500
        tool_budget: 2
        prompt_style: terse
      medium:
        max_tokens: 2000
        tool_budget: 5
        prompt_style: normal
      high:
        max_tokens: 4000
        tool_budget: 10
        prompt_style: detailed
```

## วิธี apply

```bash
# Option 1: ผมใช้ patch tool ให้ (ขอ "ทำเลย" ก่อน)
# Option 2: คุณ copy block ข้างบนไปวางเอง
```

## ข้อจำกัด

- MiniMax-M3 (deepseek-v4-flash) ไม่ใช่ reasoning model → `reasoning_effort` API param อาจไม่มีผล
- แต่ soft signal นี้จะคุม max_tokens, tool budget, prompt style จริง

## Verify หลัง apply

```bash
hermes config get agent.effort
hermes config get agent.effort.levels
```
