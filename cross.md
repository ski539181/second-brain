# cross.md — AI Rules for [[Second Brain]]

> **Schema/Rules** ที่ AI ต้องทำตามเมื่อทำงานกับ Second Brain นี้
> เปรียบเสมือน "กฎระเบียบ" ของ AI — ต้องอ่านก่อนทำงานใดๆ

## 📥 When user drops file into /raw

1. อ่านไฟล์ใน `/raw` (ล่าสุด)
2. สรุปเป็นหัวข้อสั้นๆ (3-5 bullets)
3. สร้าง **backlinks** ไปยังหัวข้อที่เกี่ยวข้องใน `/wiki` (notes.md)
4. **ตรวจสอบความขัดแย้ง** กับข้อมูลเดิม:
   - ถ้าขัด → flag ให้ user ตัดสิน
   - ถ้าเสริม → append
   - ถ้าซ้ำ → skip + note
5. อัปเดต `index.md` (สารบัญ)
6. log ใน `log.md` (ว่าทำอะไรไป)

## ❓ When user asks question

1. **ค้นหา** ใน `/wiki` ก่อน (compound knowledge)
2. ถ้าเจอ → ตอบพร้อม cite source
3. ถ้าไม่เจอ → ตอบตามที่รู้ + note "ไม่มีใน Second Brain"
4. **ห้าม hallucinate** — verify facts ก่อนส่ง

## ✏️ Style

- ใช้ bullet/list (ไม่ paragraph)
- สั้น กระชับ ไม่เยิ่นเย้อ
- เขียนเป็น Markdown (cross-platform)
- ใส่ link เมื่ออ้างอิง (backlink = neural network)

## 🛡️ Safety Rules (from Karpathy 17)

- **Verify facts** ก่อนส่ง — facts/code/math ห้ามเดา
- **Specific > vague** — ใส่ constraints/format ใน output
- **Iterate** ไม่ใช่ restart — refine based on output
- **Reasoning effort** scales quality:
  - low = routine (status check, simple Q&A)
  - medium = default (most tasks)
  - high = research/code/analysis
- **ถ้า technical** → เรียก `auto_reasoning.py --effort=medium` ก่อน
- **ดูเพิ่ม:** `~/.[[Hermes]]/notes/ai-knowledge.md`

## 🎯 Token Optimization (per Karpathy)

- **สรุป session** ลง `podcast.md` (ย่อ 50% token)
- อ่าน `podcast.md` ก่อน ถ้าเจอ → ไม่ต้องอ่านซ้ำ
- ลบ redundancy — ข้อมูลซ้ำ = token เปลือง

## 🔁 Compound Knowledge

- ข้อมูลที่สรุปวันนี้ → ใช้เป็น context พรุ่งนี้
- โครงสร้าง `/wiki` (notes.md) = growing knowledge graph
- **ยิ่งใช้ Second Brain → ยิ่งฉลาดขึ้น** (the whole point)

## 🚫 Forbidden

- ❌ แก้ไขไฟล์ใน `/raw`
- ❌ ลบไฟล์ใน `/raw` (เก็บไว้เสมอ)
- ❌ Hallucinate (สร้างข้อมูลที่ไม่มี)
- ❌ Restart from scratch (iterate แทน)
- ❌ ใช้ high effort ตลอด (แพง + ช้า)

## 📂 File Roles

| File | Role | AI permission |
|---|---|---|
| `/raw/*` | ข้อมูลดิบ | read-only |
| `/wiki/notes.md` | Second Brain | read + append |
| `index.md` | สารบัญ | read + update |
| `log.md` | บันทึกการทำงาน | append only |
| `cross.md` | กฎ AI | read-only (this file) |
| `podcast.md` | session summary | append + read |
| `[[Cron]]-decisions.md` | feedback (✅/❌) | append + read |
| `STATE.md` | system state | read + update marker |
