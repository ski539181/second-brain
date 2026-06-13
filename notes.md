# Extended Notes

Free-form reference notes. Organized by `## Topic` headers.
Grep with `search_files pattern=<keyword> path=~/.hermes/notes target=content`.

---

## User Setup (Hermes / providers)

<!-- TokenRouter, MiniMax-M3, Telegram platform, environment facts that
     are reference-only. Move here if main memory gets tight. -->

---

## Config / Tooling Tweaks

<!-- Things we set, why, what to revert. E.g. compression threshold changes. -->

---

## Troubleshooting History

<!-- Bugs we hit, root cause, fix. Grep before debugging recurring issues. -->

---

## Projects

<!-- Per-project context that may recur across sessions. -->

### Web Scraper FT Project (user building this)
- User created FT data for coding specialization using Claude Sonnet 4.6 (thinking/high)
- Topic: Web scraper (Playwright + auto-retry + CF bypass + state persistence)
- Pattern: 4 managers (Browser, Retry, Cloudflare, State) + WebScraper Facade
- Key patterns: Circuit Breaker, Atomic Write, Stealth Patches, Exponential Backoff
- 2023-era techniques — modern CF (2025-26) requires Turnstile v3 + behavioral + TLS workarounds
- Full reference: see skill `web-scraper-expert` (auto-loads on relevant topics)

---

## Gotchas & Lessons

<!-- Non-obvious facts about tools, APIs, or this environment. -->


### Cloudflare 2025-26 Bypass Upgrade Brief (added 2026-06-13, by hermes-ceo cron)
- Task: t_4a01680b (auto-created 2026-06-13 08:50)
- Verified: 2026-06-13 via GitHub API + Brave Search + direct article fetches
- Source skill: `web-scraper-expert` (states 2023-era techniques don't work on modern CF)

**TL;DR**
1. **Patchright (Node)** เป็น drop-in replacement ของ Playwright — patches `Runtime.enable`/`Console.enable`/Command Flags/Shadow Roots leaks — pushed 4 วันก่อน, 713★, Node 18+ รองรับ. **นี่คือ upgrade ที่ minimum effort ที่สุดสำหรับ Supakit.**
2. **Camoufox (Firefox)** เป็นทางเลือกถ้ายอมเปลี่ยน engine — ★9.2k, pushed 3 วันก่อน. แต่ต้องเขียน scraper ใหม่
3. **FlareSolverr** = proxy approach ไม่ต้องแก้ code — ★14.3k, pushed 8 วันก่อน, แต่ bottleneck ที่ proxy layer
4. **tls-client / curl_cffi** ใช้สำหรับ HTTP-only (ไม่ render JS) — JS rendering ยังต้อง browser
5. **Stop**: stealth patches เดิม (webdriver/navigator.plugins) **ไม่พอแล้ว** — modern CF ตรวจ CDP-level leaks ที่ patchright แก้

**1. Turnstile v3**
- v2 = visible widget ที่ user click → v3 = invisible, server-side behavioral scoring
- Signals: TLS fingerprint (JA3/JA4), browser fingerprint (canvas/audio), mouse entropy, timing, IP reputation
- Bypass path 2025-26: (a) ทำให้ browser ดูเหมือน real Chrome (patchright/camoufox) + (b) residential proxy + (c) behavioral simulation (Bezier mouse, scroll entropy)
- 2captcha/Capsolver: มี Turnstile v3 solver (~$2-3/1000) — fallback เมื่อ bypass ไม่ผ่าน, **ไม่ใช่ primary** (cost + latency)

**2. TLS fingerprint (JA3/JA4)**
- JA3 = hash of TLS Client Hello (cipher suites, extensions, elliptic curves)
- JA4 = next-gen, human-readable, more robust (FoxIO standardized 2023)
- Cloudflare ใช้ JA3+JA4 คู่กัน + IP reputation
- **Playwright ใช้ Chromium build ของตัวเอง → JA3/JA4 ไม่เหมือน real Chrome** (เป็น known issue)
- Spoof options:
  - `curl_cffi` (Python) — `impersonate="chrome120"` → ใช้ได้กับ HTTP only
  - `tls-client` (Go/Node) — same idea, multi-language
  - `utls` (Go) — low-level
  - Playwright: **ไม่มี TLS-level fix** — ต้องใช้ patchright ที่ ship custom Chromium build

**3. Tools landscape (verified via GitHub API 2026-06-13)**

| Tool | Stack | Stars | Last pushed | Playwright compat | Notes |
|------|-------|-------|-------------|-------------------|-------|
| **patchright-nodejs** | Node 18+ | 713 | 2026-06-09 (4d) | drop-in replacement | ✅ **PRIMARY PICK** |
| patchright (core) | Driver | 3,488 | 2026-06-09 | same | Chromium-based, FF/WebKit no |
| camoufox | Firefox/C++ | 9,193 | 2026-06-10 (3d) | no (own engine) | ✅ Most starred, fingerprint-level |
| nodriver | Python CDP | 4,352 | 2026-05-13 (1mo) | no | Successor to undetected-chromedriver |
| undetected-chromedriver | Python | 12,686 | 2025-07-05 (11mo) | no | ⚠️ Slowing — replaced by nodriver |
| puppeteer-extra | JS | 7,354 | 2024-07-18 (23mo) | no | ⚠️ Stale |
| FlareSolverr | Python proxy | 14,283 | 2026-06-05 (8d) | any (proxy) | ✅ Works as sidecar |
| tls-client | Go/Node | ? | 2026-06-08 (5d) | no (HTTP) | ✅ Active |
| curl_cffi | Python | ? | 2026-06-05 (8d) | no (HTTP) | ✅ Active |

**4. Behavioral detection — what triggers it (2025-26)**
- **Mouse movement**: straight line vs Bezier curve (entropy < threshold = bot)
- **Scroll**: no scroll on long page = suspicious; sudden jump = suspicious
- **Timing**: requests at exact intervals = bot; need jitter (1500-4000ms range)
- **Event ordering**: missing focus/blur/mousemove before click
- **Headless detection beyond webdriver**: missing `window.chrome.runtime`, GPU info, media devices
- **CDP leaks** (the big one): Playwright attaches CDP → exposes `Runtime.enable`/`Console.enable` even in headless mode → patchright fixes this at the binary level

**5. Recommendation for Supakit's project (Node 18+ Playwright)**

**Minimum upgrade (≤1 hour of work):**
```bash
# Replace playwright with patchright-nodejs
npm uninstall playwright
npm install patchright  # nodejs version
npx patchright install chromium  # download patched binary
```

```js
// Change in WebScraper.js
- import { chromium } from 'playwright'
+ import { chromium } from 'patchright'
```

Expected gain: passes Cloudflare's basic fingerprint checks that current stealth patches fail at. No architecture change.

**Medium upgrade (1-2 hours):**
- Add residential proxy rotation (NodeMaven, RapidProxy — both sponsor patchright)
- Add Bezier mouse movement instead of random straight lines
- Add 2captcha/capsolver as Turnstile fallback (only when patchright fails)

**Heavy upgrade (skip unless needed):**
- Switch to Camoufox (Firefox) — bigger refactor
- Move to FlareSolverr as sidecar proxy — new infrastructure

**6. Anti-patterns (stop doing in 2025-26)**
- ❌ `navigator.webdriver = undefined` alone (CDP leaks betray you)
- ❌ Fake `navigator.plugins` only (doesn't fix Runtime.enable leak)
- ❌ 2captcha as PRIMARY (cost + slow, use as fallback)
- ❌ Fixed-interval requests (CF pattern-detects)
- ❌ Sharing one page across many URLs (state fingerprint accumulates → flag)
- ❌ `headless: true` on CF sites (modern CF detects even new headless mode)
- ❌ Stealth from 2023 (the patches in `web-scraper-expert` skill — keep the retry/state/cb logic, replace the CF module)

**Sources**
- patchright: https://github.com/Kaliiiiiiiiii-Vinyzu/patchright (readme) + /patchright-nodejs (npm pkg)
- camoufox: https://github.com/daijro/camoufox
- FlareSolverr: https://github.com/FlareSolverr/FlareSolverr
- nodriver: https://github.com/ultrafunkamsterdam/nodriver
- tls-client: https://github.com/bogdanfinn/tls-client
- curl_cffi: https://github.com/yifeikong/curl_cffi
- Scrapfly turnstile guide: https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-turnstile
- 2captcha turnstile: https://2captcha.com/p/cloudflare-turnstile
- GitHub topic: https://github.com/topics/cloudflare-turnstile-bypass

---

## Daily Reviews

<!-- Auto-appended by hermes-ceo cron @ 20:00 TH.
     Format: `## Daily Review — YYYY-MM-DD` with score, lesson, improvement, priority. -->

### 2026-06-13

## Daily Review — 2026-06-13

## Second Brain (Karpathy pattern, egBoq66lCRc)

**Source:** `raw/2026-06-13_karpathy-second-brain.md` (Thai summary by user, video verified)

**Core idea:** สร้าง **ระบบนิเวศข้อมูล** ที่ AI อ่าน/เรียนรู้ได้ — ไม่ใช่แค่จด note. โตแบบทบต้น (compound knowledge)

**Tools:** Obsidian (storage) + Cursor/VS Code (agent) — แต่ Hermes + `~/.hermes/notes/` ก็ใช้ pattern เดียวกันได้

**Folder schema:**
- `/raw` — input ดิบ (read-only, ห้าม AI แก้)
- `/wiki` (notes.md) — knowledge graph (AI เขียน/อ่าน)
- `index.md` — สารบัญ
- `log.md` (cron-decisions.md) — บันทึกการทำงาน
- `cross.md` — AI rules
- `podcast.md` — session summary (save token)

**Workflow:** Ingest → Process → QA & Compound → Optimize (token-saving)

**vs RAG:**
- Wiki AI: โตได้, human-readable, ต้นทุนต่ำ, ≤1M files
- RAG: stateless, vector-only, แพง, ≥1M files

**Status (2026-06-13):** โครงสร้างติดตั้งแล้ว — `raw/`, `cross.md`, `podcast.md` ใน `~/.hermes/notes/`

**Backlinks:** → `cross.md` (rules) → `podcast.md` (sessions) → `ai-knowledge.md` (Karpathy 17)

📊 **Score:** ✅ 2 | ⚠️ 0 | ❌ 0 / Total 2

📝 **บทเรียนวันนี้:**
Research → apply loop ทำงาน — skill ที่บอกปัญหาของตัวเอง (web-scraper-expert: "2023-era ไม่ work บน 2025-26 CF") = signal ที่ดีที่สุดว่าควร update; verified data จาก GitHub API + brief 5.8KB → patch skill เพิ่ม 63 บรรทัดใน 8 นาที.

🔧 **ปรับปรุงพรุ่งนี้:**
ทั้ง 2 task วันนี้เป็น research/skill maintenance (value #2) — value #1 (revenue) และ #3 (audience/content) ยังว่าง → พรุ่งนี้ต้องหา task ที่จับต้องรายได้หรือ lead magnet ได้จริง ไม่ใช่แค่ tooling.

🎯 **Priority พรุ่งนี้:**
Apply patchright กับ FT data pipeline ของ Supakit — เปลี่ยนจาก "research เก็บไว้" เป็น "ship scraper ใหม่ที่ผ่าน CF 2025-26" (5-นาที drop-in per brief) แล้วใช้ output ป้อน content/audience.

---
