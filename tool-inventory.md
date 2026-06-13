# Hermes Tool Inventory (2026-06-13)

## System
- **Host:** Linux 6.17.0-PROot-Distro (Termux on Android)
- **Hermes:** CLI in `/data/data/com.termux/files/home/Hermes-Agent/`
- **Model:** MiniMax-M3 (deepseek-v4-flash) via TokenRouter
- **Python:** 3.14.1
- **Node:** v22.22.1
- **Java:** OpenJDK 17.0.13+1 at `/data/local/opt/jdk-17.0.13+1/`

## Installed Tools

| Tool | Path | Size | Use |
|------|------|------|-----|
| **gh CLI v2.65.0** | `/data/local/bin/gh` | 49MB | GitHub CLI |
| **Android SDK** | `/data/local/opt/android-sdk/` | ~500MB+ | APK build |
| **platform-34** | `.../platforms/android-34/` | - | API 34 |
| **build-tools** | `.../build-tools/` | - | aapt2, d8 |
| **cmdline-tools** | `.../cmdline-tools/latest/` | 146MB | sdkmanager |
| **Java JDK 17** | `/data/local/opt/jdk-17.0.13+1/` | 181MB | gradle |
| **camoufox browser** | `/root/ft-data-pipeline/camoufox-extract/` | 621MB | Firefox 150 |
| **curl_cffi (Python)** | `python3 -c "import curl_cffi"` | v0.15.0 | CF bypass |
| **patchright (npm)** | `/root/ft-data-pipeline/node_modules/patchright` | - | Playwright drop-in |
| **camoufox (npm)** | `/root/ft-data-pipeline/node_modules/camoufox` | v0.1.19 | Firefox (broken on arm64) |

## Patches Applied (camoufox npm 0.1.19 for arm64)

These patches to `node_modules/camoufox/dist/chunk-NZSG52OA.cjs` enable running on Termux/ARM64:

1. **`installedVerStr()` (line 3456)** — bypass `Version.fromPath()` which fails on non-standard install paths. Returns version from `application.ini` if `CAMOUFOX_EXEC` env is set.
2. **`launchOptions` ff_version_str (line 10716)** — read version from `application.ini` directly instead of calling `installedVerStr().split()`.
3. **`Version.fromPath` requires `release` field** in version.json (was using `version` only).

If `npm install` is re-run, these patches are lost. Re-apply or vendor the package.

## Known Limitations

- **Termux has no libgtk-3** → Firefox can't fully launch (XPCOM error). Patchright also fails because no Chromium.
- **Workaround:** Use FTScraper.py (curl_cffi) — pure HTTP, no browser needed, bypasses CF TLS checks.
- **For full browser:** Deploy to x86_64 server.

## Storage
- agent-bridge source: `/data/local/tmp/agent-bridge-source/` (cloned, build fail)
- JDK + Android SDK: `/data/local/opt/` (~1.2GB total)
- ft-data-pipeline: `/root/ft-data-pipeline/` (project)
- camoufox browser: `/root/ft-data-pipeline/camoufox-extract/` (621MB)
