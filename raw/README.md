# /raw — Raw Inputs (ถังขยะข้อมูลดิบ)

> **กฎ:** AI **ห้ามแก้ไข** ไฟล์ในโฟลเดอร์นี้
> เก็บต้นฉบับไว้ — เพื่อ trace กลับ + verify

## ประเภทที่รับ

- บทความเว็บ (Web Clipper / `curl` output)
- ไฟล์ PDF (ดาวน์โหลด, paper, e-book)
- บันทึกประชุม (transcript)
- ข้อมูล YouTube (transcript, notes จาก user)
- ไฟล์ที่ user paste เข้ามา

## Naming convention

```
YYYY-MM-DD_source-title.md
2026-06-13_karpathy-second-brain.md
2026-06-13_karpathy-17-summary.md
2026-06-13_session-tokenrouter-401.md
```

## Workflow

1. **Injest** — user (หรือ AI) drop ไฟล์เข้ามา
2. **Process** — AI อ่าน + สรุป → ย้ายสรุปไป `/wiki` (notes.md)
3. **Keep raw** — ต้นฉบับอยู่ที่เดิม (สำหรับ verify)

## ⚠️ ห้าม

- ❌ แก้ไข content ใน /raw
- ❌ ลบไฟล์ใน /raw (เก็บไว้เสมอ)
- ❌ สร้างไฟล์ใหม่ที่ไม่ใช่ input จริง (ห้าม pollute)

## ✅ ตัวอย่าง

```
/raw/
├── 2026-06-13_karpathy-second-brain.md       ← จาก user (Thai summary)
├── 2026-06-13_karpathy-17-analysis.json      ← จาก auto-fetch
└── 2026-06-13_session-m3-test.log            ← session log
```
