# Web Scraper — Pre-Deploy Checklist

> ✅ ก่อน deploy = ติ๊กทุกข้อ ถ้าขาด = เสี่ยงพัง

## 💾 State & Persistence
- [ ] state file ใช้ **atomic write** (tmp → rename)
- [ ] backup file created on every save
- [ ] SHA-256 checksum enabled (16 chars)
- [ ] recovery logic: main → backup → fresh
- [ ] auto-save ทุก N items (default 10, ไม่ใช่ทุก request)
- [ ] state schema มี version (migrate ได้)
- [ ] graceful shutdown saves state (SIGINT/SIGTERM/uncaughtException)

## 🔁 Retry & Error
- [ ] `maxRetries` configured (3-5)
- [ ] exponential backoff formula verified (base × mult^attempt)
- [ ] jitter added (ป้องกัน thundering herd)
- [ ] retryable vs non-retryable **แยกชัด**
- [ ] circuit breaker threshold (10) + reset time (60s)
- [ ] error logs มี context (URL, attempt, stack)
- [ ] 4xx errors (400, 401, 403, 404) **ไม่ retry**

## 🛡️ [[Cloudflare]]
- [ ] stealth script inject ทุก page (addInitScript)
- [ ] CF detection selectors อัพเดต + ครอบคลุม
- [ ] 2captcha API key ผ่าน env (ไม่ hardcode)
- [ ] JS challenge timeout (35s default)
- [ ] human simulation steps defined (mouse + scroll + delay)
- [ ] bypass max attempts (3 default) ก่อน throw
- [ ] user-agent ตรงเวอร์ชัน Chrome ปัจจุบัน
- [ ] Turnstile sitekey extract ทำงานกับ DOM หลายแบบ

## 🌐 Browser
- [ ] headless args ครบ (`--no-sandbox`, `--disable-blink-features=AutomationControlled`)
- [ ] viewport + userAgent realistic
- [ ] extraHTTPHeaders set (Accept-Language, Sec-Fetch-*)
- [ ] page crash handler registered
- [ ] console error logging
- [ ] browser cleanup on exit (close context + browser)
- [ ] new page on crash (reopen logic)
- [ ] canvas fingerprint randomized
- [ ] plugins + languages mocked

## 🛑 Shutdown
- [ ] SIGINT handler → save state → exit 0
- [ ] SIGTERM handler → save state → exit 0
- [ ] uncaughtException handler → save state → exit 1
- [ ] unhandledRejection handler → save state → exit 1
- [ ] `state.markCompleted()` เรียกเมื่อจบปกติ
- [ ] `state.markFailed(err)` เรียกเมื่อ crash

## ⚙️ Config & Env
- [ ] `.env.example` มี keys ครบ (SESSION_ID, CAPTCHA_API_KEY, NODE_ENV)
- [ ] `CAPTCHA_API_KEY` ผ่าน env
- [ ] `SESSION_ID` configurable (สำหรับ resume)
- [ ] `NODE_ENV` switch headless/visible mode
- [ ] log level configurable (debug/info/warn)
- [ ] config schema validated (ไม่มี key หาย)

## ⏱️ Rate Limit
- [ ] delay between requests (1.5-4s random)
- [ ] CAPTCHA poll interval (5s)
- [ ] CAPTCHA max attempts (24 × 5s = 2 นาที)
- [ ] per-host rate limit (ถ้ามีหลาย host)
- [ ] lastRequestAt tracked (delay = max(target, last+delay))

## 🧪 Testing
- [ ] test กับ URL ที่ไม่มี CF (baseline)
- [ ] test กับ URL ที่มี CF basic (JS challenge)
- [ ] test กับ URL ที่มี Turnstile
- [ ] test **resume** (kill + restart with same SESSION_ID)
- [ ] test **SIGINT** (Ctrl+C → state saved)
- [ ] test **circuit breaker** (mock failing endpoint)
- [ ] test **404 / 500** (skip vs retry behavior)
- [ ] test **[[Memory]]** (10k URLs → no leak)
- [ ] test **disk** (state file corrupted → backup recovery)

## 📊 Monitoring
- [ ] log: success/fail count + duration
- [ ] log: rate limit hits
- [ ] log: CF bypass attempts
- [ ] log: circuit breaker state changes
- [ ] log: state save events
- [ ] alert: 2captcha budget low
- [ ] alert: circuit open 3+ times/hour

## 🔒 Security
- [ ] `.env` ใน `.gitignore`
- [ ] API keys ไม่อยู่ใน source code
- [ ] CAPTCHA tokens ไม่ถูก log
- [ ] cookies ไม่ถูก persist นอก session
- [ ] user data ใน state.json ถูก encrypt (ถ้ามี)
- [ ] URL input validated (กัน SSRF)

## 🚀 Deploy
- [ ] dependencies ใน `package.json` pinned version
- [ ] Node.js version specified (>=18)
- [ ] `npx playwright install chromium` ใน setup script
- [ ] Dockerfile / startup script tested
- [ ] health check endpoint (ถ้ามี API)
- [ ] graceful shutdown tested ใน production env
