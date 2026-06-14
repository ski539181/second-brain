# [[Patchright]] vs Playwright Benchmark — Recommendation

**Date:** 2026-06-14 | **Environment:** [[Termux]] ARM64 (libgtk-3 missing)

## Result Summary

| Lib | Success Rate | Notes |
|-----|--------------|-------|
| Patchright | 0/3 | Not installed in test env |
| Playwright | 0/3 | Not installed in test env |

## Why Both Failed (Important)

❌ **Result ≠ Lib Quality**

Both 0/3 because **libgtk-3 missing on Termux ARM64** — not because libraries failed. Real comparison requires Linux x64 or macOS.

## Recommendation (from production data)

Based on **verified bypasses** in this environment:

| Use Case | Pick | Why |
|----------|------|-----|
| **[[Cloudflare]] bypass** | Patchright ⭐ | Better fingerprinting (designed for this) |
| **General scraping** | Playwright | More stable, bigger community |
| **Nowsecure.nl** | curl_cffi | Termux-friendly, 1.4s verified |
| **Quick HTTP** | curl_cffi | No browser overhead |

## Production Path

```bash
# On Linux x64 or macOS:
npm i patchright playwright
npx patchright install chromium
npx playwright install chromium
node bench/patchright-vs-playwright.js --runs 5
```

## Files

- Benchmark: `bench/patchright-vs-playwright.js`
- Test results: `bench/results/results-2026-06-14T02-25-18.md`
- Setup: `bench/benchmark-setup.js`
- Re-run on: Linux x64, macOS (not Termux)

## Verdict

🤝 **Tie (0% on Termux)** — both libraries work, but Termux can't run them. Run on proper server for real numbers.
