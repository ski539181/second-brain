# Patchright vs Playwright Benchmark

**Goal:** Hard numbers to decide which library to use for the FT data product ([[Cloudflare]] bypass).

**Why:** Supakit blocked on "ต้องเห็นข้อมูลจริงก่อน ship" — uncertainty = blocker.

## Quick start

```bash
# 1. Install (one-time)
cd ~/.[[Hermes]]/notes/bench
node benchmark-setup.js

# 2. Run benchmark
node patchright-vs-playwright.js

# 3. Custom targets / more runs
node patchright-vs-playwright.js --runs 3
node patchright-vs-playwright.js --targets https://site1.com,https://site2.com
```

## What it does

- Tests both `patchright` and `playwright` on the same Cloudflare-protected targets
- Measures: success rate, time, response size, status code
- Runs N times per target (default 1) to detect flakiness
- Outputs: CSV (raw data) + MD (human report with verdict)

## Default targets

- `https://nowsecure.nl` — classic CF challenge page
- `https://bot.sannysoft.com` — bot detection test
- `https://httpbin.org/headers` — shows User-Agent

## Output

```
bench/results-<timestamp>.csv   — raw, machine-readable
bench/results-<timestamp>.md    — summary + verdict
```

## Notes

- **[[Termux]] ARM64:** may fail with `libgtk-3 missing`. Run on Mac/Linux x64.
- **Headless mode:** both tested headless=true (no display needed).
- **Same UA:** both use realistic Chrome 120 UA to compare fairly.
- **Timeout:** 30s/page (CF challenge can take time).

## Verdict (after running)

See the MD report. It auto-generates a winner based on success rate.

## Files

- `patchright-vs-playwright.js` — main benchmark (8.3KB, single file)
- `benchmark-setup.js` — npm install helper
- `results/` — output dir (created on first run)
