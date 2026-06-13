# AI Knowledge — From Karpathy 17 Videos

> Source: 17 YouTube videos by Andrej Karpathy (2024-2025)
> Analyzed 2026-06-13. Practical takeaways for working with LLMs (like me).

## 🎬 Source Videos

**Stable Diffusion dreams (1, 2, 4, 5, 6):**
- #1 https://youtu.be/Jv1ayv-04H4 — steampunk neural networks
- #2 https://youtu.be/vEnetcj_728 — blueberry spaghetti
- #4 https://youtu.be/sM9bozW295Q — tattoos
- #5 https://youtu.be/2oKjtvYslMY — steampunk brains
- #6 https://youtu.be/kVpDARqZdrQ — psychedelic faces

**Neural Networks fundamentals (3):**
- #3 https://youtu.be/VMj-3S1tku0 — spelled-out intro to backprop

**makemore series (7-11):**
- #7 https://youtu.be/PaCmpygFfXo — Part 1: Bigrams
- #8 https://youtu.be/TCH_1BHY58I — Part 2: MLP
- #9 https://youtu.be/P6sfmUTpUmc — Part 3: Activations, BatchNorm
- #10 https://youtu.be/q8SA3rM6ckI — Part 4: Backprop Ninja
- #11 https://youtu.be/t3YJ5hKiMQ0 — Part 5: WaveNet

**GPT series (12, 14, 15):**
- #12 https://youtu.be/kCc8FmEb1nY — Let's build GPT from scratch
- #14 https://youtu.be/zduSFxRajkE — GPT Tokenizer
- #15 https://youtu.be/l8pRSuU81PU — Reproduce GPT-2 (124M)

**LLM intro (13, 16, 17):**
- #13 https://youtu.be/zjkBMFhNj_g — [1hr Talk] Intro to LLMs
- #16 https://youtu.be/7xTGNNLPyMI — Deep Dive into LLMs like ChatGPT
- #17 https://youtu.be/EWvNQjAaOHw — How I use LLMs

---

## 🔑 10 Actionable Insights for Using LLMs

### 1. 🤖 LLM = "next token predictor"
ไม่ได้ "คิด" จริง — แค่ทำนายคำถัดไปจาก context. ทุกคำตอบ = statistical pattern matching.
- **ใช้:** อย่าคาดว่า AI "เข้าใจ" เหมือนคน — มัน predict ไม่ใช่ reason
- **อย่า:** ถามความเห็น subjective → จะได้ confident-sounding bullshit

### 2. 📋 Context = ทุกอย่าง
ทุกอย่างที่ AI ตอบ = based on context (system prompt + history + user message). ยิ่ง context ชัด ยิ่งตอบดี.
- **ใช้:** ใส่ background, constraints, examples ใน prompt
- **อย่า:** คาดว่า AI "รู้" เรื่องของคุณ — ต้องบอก

### 3. ✏️ Specific > Vague
"เขียน function บวกเลข" < "เขียน Python function รับ list[int] คืน int ผลรวม, ใช้ reduce, handle empty list"
- **ใช้:** ระบุ format, length, style, constraints
- **อย่า:** "ช่วยหน่อย", "ทำให้ดีๆ"

### 4. 🚨 Hallucination จริง
AI มั่นใจผิดได้ — โดยเฉพาะ facts, code, math. เคยเจอ: บอก "key เก่าใช้ได้" แต่จริงๆ 401
- **ใช้:** Verify facts ก่อนใช้ (test, search, double-check)
- **อย่า:** เชื่อ AI 100% — โดยเฉพาะ specific numbers/names/dates

### 5. 🔄 Iterate
รอบแรกไม่ดี ≠ AI แย่ — แปลว่า prompt ต้องปรับ. Refine prompt → better answer.
- **ใช้:** ถ้าไม่ดี บอก "ทำ X แต่ Y ผิด → แก้" แทน "ทำใหม่"
- **อย่า:** เริ่มใหม่ทุกครั้ง — เสีย context

### 6. 🎚️ Reasoning effort มีผลจริง
เหมือนที่เราทำวันนี้ (low/medium/high) — quality + speed + cost เปลี่ยน
- **ใช้:** low = routine, medium = default, high = research/code
- **อย่า:** high ทุกอย่าง (แพง + ช้า)

### 7. 🔤 Tokenization matters
คำภาษาไทย = หลาย token. "สวัสดี" อาจ = 4-5 tokens, แต่ "hello" = 1 token
- **ใช้:** ผสม EN/TH เมื่อเหมาะสม
- **อย่า:** คาดว่า AI นับ tokens เหมือนคน

### 8. 🧠 ไม่มี memory ข้าม session
ผมจำอะไรใน conversation นี้ได้ แต่ session ใหม่ = เริ่มใหม่. ใช้ memory + notes แทน
- **ใช้:** บอก "จำไว้ว่า..." + ให้ผม save ลง memory
- **อย่า:** คาดว่า AI จำ project ของคุณข้ามวัน

### 9. 🏗️ Architecture มีขีดจำกัด
Transformer = no real-time learning, no perfect logic, ไม่ใช่ "intelligence" ในแบบทั่วไป
- **ใช้:** AI = tool ที่เก่ง pattern matching + generation
- **อย่า:** คาดว่า AI จะ "เรียนรู้" จาก feedback ใน 1 call

### 10. 🌡️ Temperature/effort เปลี่ยน behavior
Temperature 0 = deterministic, 1 = creative. effort = ความลึกของ reasoning
- **ใช้:** low effort + temperature 0 = facts/code (แม่น)
- **อย่า:** creative writing ที่ temp=0 = น่าเบื่อ

---

## 🎬 Recommended Viewing Order (ถ้ามีเวลาจำกัด)

1. **#13 (1hr Talk)** — mental model ของ LLMs (พื้นฐานสุด)
2. **#17 (How I use LLMs)** — practical tips (ใช้ได้ทันที)
3. **#3 (Backprop)** — เข้าใจ neural network ไม่งง
4. **#12 (Let's build GPT)** — architecture (ละเอียด)

**รวม: 4 คลิป ~3-4 ชม.** — เข้าใจ 80% ของ LLM

---

## 🔗 Related

- `~/.hermes/notes/STATE.md` — current system state
- `~/.hermes/notes/tokenrouter-reasoning.md` — M3 + effort
- `~/.hermes/notes/auto-reasoning-test.md` — our own tests
- `~/.hermes/skills/web-scraper-expert/SKILL.md` — scraper skill
- `MEMORY.md` — cross-session facts
