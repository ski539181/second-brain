# Web Scraper — Decision Tree (เมื่อไหร่ทำอะไร)

> เจอสถานการณ์ → เดินตามกิ่ง → รู้ทันทีว่าต้องทำอะไร

## 🌳 เริ่มต้น — URL ใหม่เข้ามา
```
URL ใหม่
  ├─ มีใน Kanban/queue แล้ว? → ✅ skip (dedup)
  ├─ เกิน rate limit? → ⏱️ wait until OK
  └─ เริ่ม retry loop → ↓
```

## 🌳 During Retry Loop — attempt ไหน?
```
attempt = 0-2  → ลองตามปกติ (delay 1-4s)
attempt = 3-4  → เพิ่ม delay (exponential)
attempt = 5+   → circuit breaker check
10 fails ติด   → 🔴 OPEN circuit 60s
```

## 🌳 ได้ Error → Retryable?
```
Error?
  ├─ 4xx (400, 401, 403, 404)   → ❌ skip (ไม่มีวันสำเร็จ)
  ├─ 429 (rate limit)            → ⏱️ wait 2x delay, retry
  ├─ 5xx (500-504)               → 🔄 retry (server มีปัญหา)
  ├─ Network (ECONNRESET, etc.)  → 🔄 retry (transient)
  ├─ Browser crash               → 🔧 reopen page, continue
  └─ Circuit open                → 🚫 reject immediately
```

## 🌳 เจอ [[Cloudflare]] → Bypass Strategy
```
Challenge detected
  ├─ 1. Stealth OK? → continue
  │     └─ fail ↓
  ├─ 2. JS auto-resolve ใน 35s? → wait
  │     └─ fail ↓
  ├─ 3. Turnstile + API key? → 2captcha
  │     └─ fail ↓
  ├─ 4. Human sim (mouse + scroll) → try
  │     └─ fail ↓
  └─ 5. ❌ throw → retry whole flow (max 3 attempts)
```

## 🌳 State Save — เมื่อไหร่?
```
Event
  ├─ ทุก N items (default 10) → 💾 auto-save
  ├─ Before shutdown (SIGINT)  → 💾 save ทันที
  ├─ On error (caught)         → 💾 save + mark failed
  ├─ On circuit open           → 💾 save current index
  └─ On completion            → 💾 final save
```

## 🌳 Circuit Breaker — อยู่ state ไหน?
```
State
  ├─ CLOSED   → ทำงานปกติ, นับ failures
  │   └─ 10 fails ติด → OPEN
  ├─ OPEN     → reject ทุก request
  │   └─ 60s ผ่าน → HALF-OPEN
  └─ HALF-OPEN → ทดสอบ 1 request
      ├─ success → CLOSED (reset failures)
      └─ fail    → OPEN (reset 60s ใหม่)
```

## 🌳 Rate Limit — delay เท่าไหร่?
```
Delay between requests
  ├─ < 1,500ms   → ⚠️ โดน ban (เร็วไป)
  ├─ 1,500-4,000ms → ✅ ปลอดภัย (default)
  └─ > 4,000ms   → 🐌 ช้าเกินไป (เสียเวลา)
```

## 🌳 เจอ Error แบบไหน → ใช้ tool อะไร?
```
Scenario                  → Action
─────────────────────────────────────────
Page ไม่โหลด             → waitForLoadState + timeout
Element ไม่เจอ            → waitForSelector + retry
ข้อมูลเปลี่ยน layout      → ใช้ multiple selectors
Infinite scroll            → scroll + wait
Login required             → save state + alert
Cookie expired             → re-login flow
```

## 🌳 เมื่อไหร่ต้อง Update Browser?
```
Trigger
  ├─ 401/403 → 🍪 clear cookies + retry
  ├─ Page crash → 🔧 new page
  ├─ Context corrupted → 🆕 new context
  ├─ IP rate-limited → 🔄 restart browser (new IP)
  └─ [[Memory]] > 80% → 🔄 restart browser
```

## 🌳 เมื่อไหร่ควรหยุด (kill switch)?
```
Stop condition
  ├─ User กด Ctrl+C → save + exit
  ├─ Circuit open + delay exhausted → exit
  ├─ Disk เต็ม → save + exit
  ├─ API key หมดอายุ → save + alert
  └─ URLs หมด → mark completed + exit
```
