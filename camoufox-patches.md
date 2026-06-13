# Camoufox arm64 Patches (2026-06-13)

## Why these patches

camoufox 0.1.19 npm package has a `Version.fromPath()` bug on non-standard install paths. On [[Termux]] (Android aarch64), the standard install location doesn't exist, so the function returns `undefined` and `.split()` crashes.

## Files patched

`/root/ft-data-pipeline/node_modules/camoufox/dist/chunk-NZSG52OA.cjs`

### Patch 1: `installedVerStr()` (line 3456)

**Before:**
```js
function installedVerStr() {
  return _Version.fromPath().fullString;
}
```

**After:**
```js
function installedVerStr() {
  // Patch: bypass Version.fromPath() which fails on non-standard install paths (arm64)
  const execPath = process.env.CAMOUFOX_EXEC;
  if (execPath) {
    try {
      const iniPath = require('path').join(require('path').dirname(execPath), 'application.ini');
      if (require('fs').existsSync(iniPath)) {
        const ini = require('fs').readFileSync(iniPath, 'utf-8');
        const match = ini.match(/Version=([\d.]+)/);
        if (match) return match[1] + 'camoufox';
      }
    } catch (e) { /* fallthrough */ }
  }
  try {
    const v = Version.fromPath();
    if (v && v.fullString) return v.fullString;
  } catch (e) { /* fallthrough */ }
  return '150.0.2camoufox';
}
```

### Patch 2: `launchOptions` ff_version_str (line 10716)

**Before:**
```js
ff_version_str = installedVerStr().split(".", 1)[0];
```

**After:**
```js
// Patch: read from application.ini directly (camoufox 0.1.19 Version.fromPath is broken on arm64)
try {
  const _execPath = process.env.CAMOUFOX_EXEC || (executable_path || '');
  const _ini = require('fs').readFileSync(require('path').join(require('path').dirname(_execPath), 'application.ini'), 'utf-8');
  const _m = _ini.match(/Version=([\d.]+)/);
  ff_version_str = _m ? _m[1].split('.', 1)[0] : '150';
} catch (e) {
  ff_version_str = '150';
}
```

### Patch 3: `version.json` format

**File:** `/root/.cache/camoufox/version.json`

**Before:**
```json
{"version": "150.0.2", "browser": "camoufox", "path": "..."}
```

**After (required `release` field):**
```json
{"release": "150.0.2", "version": "150.0.2-20250612120000"}
```

## Re-applying after `npm install`

These patches are LOST on `npm install`. Re-apply with:

```bash
# Patch 1+2 (file edit):
# See diff above
# Patch 3:
echo '{"release":"150.0.2","version":"150.0.2-20250612120000"}' \
  > /root/.cache/camoufox/version.json
```

Or vendor the package: copy `node_modules/camoufox` to a git repo and add a post-install script.

## Environment vars needed

- `CAMOUFOX_EXEC=/path/to/camoufox-bin` — absolute path to the binary
- Symlink: `/root/.cache/camoufox/camoufox-bin` → actual binary
- Binary needs `chmod +x`

## Why this still fails on Termux

After all 3 patches, the camoufox binary launches but fails on `libgtk-3.so.0: cannot open shared object file` — Termux doesn't ship GTK. **Use [[FTScraper]].py ([[curl_cffi]]) for HTTP-only scraping.**
