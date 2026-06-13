# FT Data Pipeline

Web scraper for FT (fine-tuning) data using **patchright** (Playwright drop-in) with **camoufox** fallback for [[Cloudflare]] 2025-26 bypass.

## Quick Start

```bash
npm install
node [[WebScraper]].js <url> [selector]
```

## Why patchright?

Per the 2025-26 Cloudflare brief (`../../notes.md`):
- Patches CDP-level leaks that modern CF detects: `Runtime.enable`, `Console.enable`, Command Flags, Closed Shadow Roots
- Drop-in replacement for Playwright (just change the import)

## Why camoufox fallback?

- Firefox-based, more robust against fingerprinting
- Works on arm64 Linux (patchright doesn't)
- Auto-activated if patchright fails

See `WebScraper.js` for the implementation.


## ✅ Tested

`[[FTScraper]].py` (curl_cffi HTTP fallback) **bypasses nowsecure.nl** (Cloudflare challenge) in ~1.4s on Termux ARM64. No browser binary needed.

```bash
pip install curl_cffi
python FTScraper.py https://nowsecure.nl
```

See `FTScraper.py` for full API. Use `WebScraper.js` for browser-based scraping (needs x86_64 Linux + libgtk-3 for Firefox).
