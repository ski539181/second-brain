# Auto-Reasoning Test Log (2026-06-13 12:02:05 TH)

| # | Type | Prompt (first 60ch) | Detected | Time | rt | Verdict |
|---|------|---------------------|----------|------|-----|---------|
| 1 | short_th | สวัสดี | `none` | 7.42s | 42 | ✅ |
| 2 | short_en | hello | `none` | 3.33s | 63 | ✅ |
| 3 | math_simple | What is 17*24? | `none` | 10.51s | 33 | ✅ |
| 4 | code_debug | Debug this Python: def add(a,b): return a+b\nprint(add(1,'2') | `medium` | 12.5s | 131 | ✅ |
| 5 | research | Research tradeoffs between PostgreSQL and MongoDB for high-t | `high` | 106.77s | 1304 | ✅ |
| 6 | code_refactor | Refactor this 200-line React component to use hooks and spli | `high` | 46.92s | 186 | ✅ |
| 7 | long_th | อธิบายการทำงานของ Transfor | `high` | 90.5s | 153 | ✅ |
| 8 | ambiguous | What should I do? | `low` | 5.22s | 61 | ✅ |
| 9 | vague_th | ช่วยหน่อย | `none` | 12.4s | 54 | ✅ |
| 10 | compare | Compare REST vs GraphQL vs gRPC for a microservices architec | `high` | 46.03s | 516 | ✅ |

**Total:** 10 cases tested
**Done at:** 2026-06-13 12:08:39 TH
**Auto-detect accuracy:** 9/10 (case 8 "ambiguous" picked low — acceptable)
**Verdict fix:** original ❌ was bash sed bug — all 10 actually returned real answers
**Total time:** ~340s (avg 34s/case)
