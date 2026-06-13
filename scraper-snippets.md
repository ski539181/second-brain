# Web Scraper — Code Snippets (Copy-Paste Ready)

> เขียนครั้งเดียว ใช้ได้ทุก project — copy block ได้เลย

## 1️⃣ Exponential Backoff with Jitter
```javascript
function computeDelay(attempt, base = 1000, mult = 2, jitter = 1000, max = 30000) {
  const exp = base * Math.pow(mult, attempt);
  const noise = Math.random() * jitter;
  return Math.min(exp + noise, max);
}
```

## 2️⃣ Atomic File Write
```javascript
import fs from "fs/promises";

async function atomicWrite(path, data) {
  const tmp = `${path}.tmp`;
  const backup = `${path}.backup`;
  await fs.writeFile(tmp, JSON.stringify(data, null, 2));
  try { await fs.copyFile(path, backup); } catch {}  // skip if no main
  await fs.rename(tmp, path);  // OS atomic
}
```

## 3️⃣ SHA-256 Checksum (16 chars)
```javascript
import crypto from "crypto";

function checksum(data) {
  return crypto
    .createHash("sha256")
    .update(JSON.stringify(data))
    .digest("hex")
    .substring(0, 16);
}
```

## 4️⃣ Stealth: Hide Webdriver
```javascript
Object.defineProperty(navigator, "webdriver", {
  get: () => undefined,
  configurable: true,
});
try { delete Object.getPrototypeOf(navigator).webdriver; } catch {}
```

## 5️⃣ Stealth: Fake window.chrome
```javascript
if (!window.chrome) {
  window.chrome = {
    runtime: {
      id: undefined,
      connect: () => ({ postMessage: () => {}, disconnect: () => {} }),
      sendMessage: () => {},
      onMessage: { addListener: () => {} },
    },
    loadTimes: () => ({
      requestTime: Date.now() / 1000,
      startLoadTime: Date.now() / 1000,
      commitLoadTime: Date.now() / 1000,
      finishDocumentLoadTime: Date.now() / 1000,
      finishLoadTime: Date.now() / 1000,
      firstPaintTime: Date.now() / 1000,
      navigationType: "Other",
      wasFetchedViaSpdy: true,
      npnNegotiatedProtocol: "h2",
      connectionInfo: "h2",
    }),
    csi: () => ({ startE: Date.now(), onloadT: Date.now(), pageT: 0, tran: 15 }),
    app: { isInstalled: false, getDetails: () => null, getIsInstalled: () => {} },
  };
}
```

## 6️⃣ Stealth: Fake Plugins
```javascript
Object.defineProperty(navigator, "plugins", {
  get: () => {
    const plugins = [
      { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "Portable Document Format" },
      { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: "" },
      { name: "Native Client", filename: "internal-nacl-plugin", description: "" },
    ];
    Object.defineProperty(plugins, "length", { value: plugins.length });
    plugins.item = (i) => plugins[i];
    plugins.namedItem = (n) => plugins.find(p => p.name === n) || null;
    plugins.refresh = () => {};
    return plugins;
  },
});

Object.defineProperty(navigator, "languages", { get: () => ["en-US", "en"] });
```

## 7️⃣ Stealth: Permissions Override
```javascript
const origQuery = window.navigator.permissions.query.bind(navigator.permissions);
window.navigator.permissions.query = (params) => {
  if (params.name === "notifications") {
    return Promise.resolve({ state: Notification.permission, onchange: null });
  }
  return origQuery(params);
};
```

## 8️⃣ Stealth: Canvas Fingerprint Random
```javascript
const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function (type, ...args) {
  const ctx = this.getContext("2d");
  if (ctx) {
    const img = ctx.getImageData(0, 0, this.width, this.height);
    for (let i = 0; i < img.data.length; i += 4000) {
      img.data[i] = img.data[i] ^ ((Math.random() * 2) | 0);
    }
    ctx.putImageData(img, 0, 0);
  }
  return origToDataURL.call(this, type, ...args);
};
```

## 9️⃣ Circuit Breaker (Simple Class)
```javascript
class CircuitBreaker {
  constructor(threshold = 10, resetMs = 60000) {
    this.failures = 0;
    this.open = false;
    this.threshold = threshold;
    this.resetMs = resetMs;
    this.timer = null;
  }
  
  recordFailure() {
    this.failures++;
    if (this.failures >= this.threshold && !this.open) {
      this.open = true;
      this.timer = setTimeout(() => {
        this.open = false;
        this.failures = 0;
        console.log("🟡 Circuit HALF-OPEN");
      }, this.resetMs);
    }
  }
  
  recordSuccess() { this.failures = 0; }
  canRequest() { return !this.open; }
}
```

## 🔟 Retry Wrapper (with Circuit Breaker)
```javascript
async function withRetry(fn, options = {}) {
  const { maxRetries = 5, base = 1000, mult = 2, jitter = 1000, max = 30000,
          isRetryable = () => true, onRetry = () => {} } = options;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt === maxRetries || !isRetryable(err)) throw err;
      const delay = computeDelay(attempt, base, mult, jitter, max);
      onRetry({ attempt, delay, error: err });
      await new Promise(r => setTimeout(r, delay));
    }
  }
}
```

## 1️⃣1️⃣ Random Sleep (Rate Limit)
```javascript
function sleep(min, max) {
  const ms = min + Math.random() * (max - min);
  return new Promise(r => setTimeout(r, ms));
}
// Usage: await sleep(1500, 4000);
```

## 1️⃣2️⃣ Graceful Shutdown
```javascript
function setupShutdown(saveState) {
  const handler = async (signal, err) => {
    console.log(`\n📡 ${signal} — saving state...`);
    if (err) console.error("Error:", err);
    try { await saveState(); } catch {}
    process.exit(err ? 1 : 0);
  };
  process.on("SIGINT", () => handler("SIGINT"));
  process.on("SIGTERM", () => handler("SIGTERM"));
  process.on("uncaughtException", (err) => handler("uncaughtException", err));
  process.on("unhandledRejection", (reason) => handler("unhandledRejection", new Error(String(reason))));
}
```

## 1️⃣3️⃣ CF Detection (Title + DOM)
```javascript
async function isCFPresent(page) {
  try {
    const title = (await page.title()).toLowerCase();
    if (title.includes("just a moment") || 
        title.includes("checking your browser") || 
        title.includes("attention required")) {
      return true;
    }
    return await page.evaluate(() => 
      !!document.querySelector("#cf-wrapper, #challenge-form, .cf-turnstile, [data-sitekey]")
    );
  } catch { return false; }
}
```

## 1️⃣4️⃣ Human Mouse Simulation
```javascript
async function simulateHuman(page) {
  const vp = page.viewportSize() || { width: 1920, height: 1080 };
  for (let i = 0; i < 4; i++) {
    const x = 100 + Math.random() * (vp.width - 200);
    const y = 100 + Math.random() * (vp.height - 200);
    await page.mouse.move(x, y, { steps: 15 + Math.floor(Math.random() * 10) });
    await sleep(200, 600);
  }
  await page.evaluate(() => window.scrollBy({ top: 80 + Math.random() * 150, behavior: "smooth" }));
  await sleep(1000, 1500);
}
```

## 1️⃣5️⃣ 2captcha Submit + Poll
```javascript
async function solveTurnstile(page, apiKey, maxPolls = 24, pollMs = 5000) {
  const sitekey = await page.evaluate(() => 
    document.querySelector(".cf-turnstile, [data-sitekey]")?.dataset?.sitekey
  );
  if (!sitekey) throw new Error("Turnstile sitekey not found");
  
  // Submit
  const submit = await fetch("https://2captcha.com/in.php", {
    method: "POST",
    body: new URLSearchParams({ key: apiKey, method: "turnstile", sitekey, pageurl: page.url(), json: "1" }),
  }).then(r => r.json());
  if (submit.status !== 1) throw new Error(`2captcha submit: ${submit.request}`);
  
  // Poll
  for (let i = 0; i < maxPolls; i++) {
    await sleep(pollMs, pollMs);
    const result = await fetch(
      `https://2captcha.com/res.php?key=${apiKey}&action=get&id=${submit.request}&json=1`
    ).then(r => r.json());
    if (result.status === 1) return result.request;
    if (result.request !== "CAPCHA_NOT_READY") throw new Error(`2captcha: ${result.request}`);
  }
  throw new Error("Turnstile solve timeout");
}
```

## 1️⃣6️⃣ Extract + Save to State
```javascript
async function extractAndSave(page, url, currentIndex, stateManager) {
  const data = await page.evaluate(() => ({
    title: document.title,
    text: document.body?.innerText?.slice(0, 1000) || "",
    timestamp: new Date().toISOString(),
  }));
  stateManager.updateProgress(currentIndex, { url, ...data }, true);
}
```

## 1️⃣7️⃣ URL Resume (Read State)
```javascript
async function getResumeIndex(stateFile) {
  try {
    const state = JSON.parse(await fs.readFile(stateFile, "utf-8"));
    return state.progress?.currentIndex ?? 0;
  } catch {
    return 0;  // Fresh start
  }
}
```

## 1️⃣8️⃣ Browser Args (Hardened)
```javascript
const BROWSER_ARGS = [
  "--no-sandbox",
  "--disable-setuid-sandbox",
  "--disable-blink-features=AutomationControlled",  // ← key for stealth
  "--disable-dev-shm-usage",
  "--disable-infobars",
  "--disable-extensions",
  "--no-first-run",
  "--disable-default-apps",
  "--window-size=1920,1080",
  "--disable-gpu",
  "--disable-software-rasterizer",
];
```

## 1️⃣9️⃣ Playwright Launch (with args)
```javascript
import { chromium } from "playwright";

const browser = await chromium.launch({
  headless: false,  // production: true
  slowMo: 50,       // human-like delay
  args: BROWSER_ARGS,
});

const context = await browser.newContext({
  viewport: { width: 1920, height: 1080 },
  userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  locale: "en-US",
  timezoneId: "America/New_York",
  extraHTTPHeaders: {
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    DNT: "1",
    "Upgrade-Insecure-Requests": "1",
  },
});
```

## 2️⃣0️⃣ State Schema (Template)
```javascript
const initialState = () => ({
  version: "1.0.0",
  sessionId: null,
  status: "idle",  // idle | running | paused | completed | failed
  startTime: null,
  endTime: null,
  lastUpdated: null,
  lastError: null,
  progress: {
    totalItems: 0,
    currentIndex: 0,
    processedItems: 0,
    successItems: 0,
    failedItems: 0,
  },
  results: [],
  errors: [],
});
```
