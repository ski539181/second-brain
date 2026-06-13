# Web Scraper — Quick Reference (Cheat Sheet)

> One-page lookup สำหรับลืมสูตร/pattern → เปิดดู 2 วิ

## 🔁 Retry Formula
```
delay = min(base × multiplier^attempt + random(0, jitterMax), maxDelay)
```
**Defaults:** base=1000ms, multiplier=2, jitterMax=1000, max=30000
**Jitter = ป้องกัน thundering herd** (scraper หลายตัว retry พร้อมกัน)

---

## ⚡ Circuit Breaker States
```
CLOSED ──[10 fails]──► OPEN ──[60s]──► HALF-OPEN ──[success]──► CLOSED
   │                                       │
   └────────────[fail]─────────────────────┘ (กลับ OPEN)
```

---

## 💾 State Persistence (Atomic Write)
```
1. เขียน state.json.tmp
2. backup state.json → state.json.backup
3. fs.rename(tmp → state.json)   # OS atomic
4. corrupt? → โหลด backup → ถ้า backup เสีย → fresh start
```

---

## 🌐 HTTP Status Codes
| Code | Action |
|---|---|
| 408, 429, 500, 502, 503, 504 | 🔄 Retry |
| 400, 401, 403, 404 | ❌ Skip (ไม่ retry) |

---

## 🛡️ [[Cloudflare]] Bypass Waterfall
```
1. Stealth patches (navigator, plugins, permissions)
   ↓ fail
2. Wait for JS auto-resolve (35s timeout)
   ↓ fail
3. Turnstile via 2captcha (sitekey → token → inject)
   ↓ fail
4. Human simulation (mouse + scroll + delay)
   ↓ fail
5. Throw → retry whole flow
```

---

## 🕵️ Browser Stealth — Key Items
- **Flags:** `--disable-blink-features=AutomationControlled`, `--no-sandbox`
- **`navigator.webdriver` =** `undefined`
- **`window.chrome`** = `{ runtime, loadTimes, app }`
- **`navigator.plugins`** = `[3 fake plugins]`
- **`navigator.languages`** = `['en-US', 'en']`
- **Canvas** = randomize pixels (XOR 1 bit ทุก 4000 bytes)

---

## 🚨 Error Patterns (Retryable)
- `ECONNRESET`, `ETIMEDOUT`, `ECONNREFUSED`
- `ERR_NETWORK*`
- `Navigation timeout`
- `Target closed`, `Page crashed`, `Protocol error`

---

## ⏱️ Rate Limit Defaults
| Action | Delay |
|---|---|
| Between requests | 1,500-4,000ms (random) |
| 2captcha poll | 5,000ms (max 24 attempts) |
| CF wait | 35,000ms timeout |
| Auto-save | every 10 items |

---

## 🔐 2captcha Quick Flow
```javascript
// 1. Submit
POST https://2captcha.com/in.php
  key=API_KEY, method=turnstile, sitekey=X, pageurl=URL

// 2. Poll
GET https://2captcha.com/res.php
  key=API_KEY, action=get, id=TASK_ID
  → "CAPCHA_NOT_READY" | token

// 3. Inject
document.querySelector('[name="cf-turnstile-response"]').value = TOKEN
form.submit()
```
