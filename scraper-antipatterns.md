# Web Scraper — Anti-Patterns (อย่าทำเด็ดขาด)

> รวม "ข้อผิดพลาดที่เจอบ่อย" → กันพลาดก่อนพัง production

## 💾 State & Persistence — ❌ อย่าทำ
- ❌ `fs.writeFile('state.json', data)` ตรงๆ → ไม่ atomic, ไฟล์อาจเสียกลางทาง
- ❌ เก็บ results ใน memory ไม่จำกัด → OOM เมื่อ URLs เยอะ
- ❌ ไม่มี checksum → corruption ตรวจไม่เจอ, resume ผิดพลาด
- ❌ ไม่ backup state → ไฟล์หาย = เริ่มใหม่หมด
- ❌ save checkpoint ทุก request → I/O bottleneck (ช้ามาก)
- ❌ ใช้ `JSON.stringify(state)` ซ้อน → circular reference crash

## 🔁 Retry & Error — ❌ อย่าทำ
- ❌ retry ไม่จำกัด (infinite loop) → DDoS ตัวเอง + ban IP
- ❌ retry 4xx errors → waste time, ไม่มีวันสำเร็จ
- ❌ ไม่แยก retryable/non-retryable → ลองซ้ำของเดิมไม่จบ
- ❌ ไม่มี circuit breaker → hammer server ที่ down
- ❌ sleep fixed delay (เช่น 1s ทุกครั้ง) → thundering herd
- ❌ catch error เงียบๆ → ไม่รู้ว่าพังตรงไหน
- ❌ log error message แต่ไม่ log context (URL, attempt, stack)

## 🛡️ Cloudflare Bypass — ❌ อย่าทำ
- ❌ ลบ `webdriver` flag อันเดียว → CF ตรวจ 6+ จุด
- ❌ ลืม randomize canvas fingerprint → ตรวจได้ (hash ตรง)
- ❌ ใช้ 2captcha โดยไม่มี API key → 500 error, retry ไม่จบ
- ❌ ไม่ handle JS challenge timeout → stuck ตลอด
- ❌ skip CF detection (assume "น่าจะไม่มี") → โดน block ทุก request
- ❌ ใช้ user-agent เก่า (Chrome/120 ตอนนี้ Chrome/125) → ตรวจทันที
- ❌ hardcode Turnstile sitekey → เปลี่ยน = พัง

## 🌐 Browser — ❌ อย่าทำ
- ❌ `headless: true` แต่ไม่ apply stealth → ตรวจทันที
- ❌ share context ระหว่าง sessions → leak cookies, contaminate state
- ❌ ไม่ handle page crash → lose all progress
- ❌ `slowMo: 0` + headless → ตรวจได้ง่าย (human ไม่ทำอะไรเร็วขนาดนั้น)
- ❌ ใช้ `--no-sandbox` ใน production โดยไม่จำเป็น → security risk

## 💰 Resource & Cost — ❌ อย่าทำ
- ❌ ไม่ dispose browser เมื่อ done → memory leak
- ❌ ไม่ handle SIGINT → state หาย, resume ไม่ได้
- ❌ log ทุก request (debug level) → disk เต็มเร็ว
- ❌ ไม่ set timeout → ค้างตลอด, กิน resources
- ❌ เปิด browser ใหม่ทุก URL → ช้ามาก, CF สังเกตได้

## 🏗️ Architecture — ❌ อย่าทำ
- ❌ รวม logic ทุกอย่างใน 1 file (1000+ lines) → แก้ยาก test ยาก
- ❌ ไม่แยก `extractFn` → scraper ผูกกับ business logic, ใช้ซ้ำไม่ได้
- ❌ hardcode config ใน source code → แก้ทุกครั้งที่ deploy
- ❌ ไม่มี logger (ใช้ `console.log`) → format มั่ว, search ยาก
- ❌ copy-paste retry logic หลายที่ → แก้ที่เดียวไม่ได้

## 🔒 Security — ❌ อย่าทำ
- ❌ commit `.env` ลง git → key หลุด
- ❌ hardcode API keys ใน source → ดูได้จาก repo
- ❌ log CAPTCHA token / cookies → ข้อมูล sensitive หลุด
- ❌ เก็บ user data ใน state.json → โดนขโมยง่าย
- ❌ ไม่ validate URL input → SSRF (server-side request forgery)

## ✅ Quick Test: ทำอันนี้ก่อนเปิดใช้
- [ ] kill scraper กลางทาง → restart ด้วย SESSION_ID เดิม → resume ได้มั้ย?
- [ ] กด Ctrl+C → state.json อัพเดตมั้ย?
- [ ] ลอง URL ที่มี CF → bypass ผ่านมั้ย?
- [ ] mock ให้ server fail 10 ครั้งติด → circuit open มั้ย?
- [ ] disk เต็ม → error handle graceful มั้ย?
