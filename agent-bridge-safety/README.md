# agent-bridge Safety System (2026-06-13)

## What
5-layer safety wrapper for SteveJuniorMC/agent-bridge (Android screen control).

## Files
- `policy.yaml` (3,295 bytes) — config: network, apps, rate limit, AI/SMS, kill switch
- `safety_wrapper.py` (7,090 bytes) — Python wrapper enforces policy

## Token
`b9d27fb6c552f1dbd2676655f14bfe06` (openssl rand -hex 16)

## 5 layers
1. **Network lockdown** — 127.0.0.1 only + token auth
2. **App whitelist** — Obsidian, Settings, Installer / blacklist banking/messages
3. **Rate limit** — 20/min, 200/hr, pause 3s every 5 taps
4. **AI/SMS/Calls** — DISABLED
5. **Kill switch** — "หยุด agent" voice command stops

## Why not used
- agent-bridge APK build failed (AAPT2 daemon, PROot env issue)
- libgtk-3 missing on Termux for camoufox (Firefox can't launch)
- curl_cffi (HTTP-only) is sufficient for FT scraping — no browser needed
- This safety system is ready if user deploys agent-bridge to x86_64 server
