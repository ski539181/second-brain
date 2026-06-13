# [[Hermes]] Patch — Forward `reasoning_effort` to [[TokenRouter]] (M3)

**Status:** PREPARED, NOT APPLIED — review diff + run `apply.sh` to install

**Goal:** When M3 (via TokenRouter) is called, auto-forward `reasoning_effort` to the API as a top-level param (where M3 reads it).

**Why this patch:** Currently `_supports_reasoning_extra_body()` in run_agent.py returns False for TokenRouter, and even if True, the field name is `reasoning` (OpenRouter-style) not `reasoning_effort` (TokenRouter-style). M3 ignores `reasoning` field — needs `reasoning_effort` at top level.

## Files affected
- `/usr/local/lib/python3.14/dist-packages/run_agent.py` (1 location)
- `/root/.hermes/config.yaml` (1 line)

## Safety
- Backup created: `run_agent.py.bak.<timestamp>` (838KB)
- Rollback: `bash ~/.hermes/scripts/rollback_hermes_reasoning_patch.sh`
- Opt-in: config flag `enable_reasoning_effort: false` (default off)

---

## Patch #1: Add TokenRouter to supported reasoning providers

**File:** `run_agent.py` line ~10087 (inside `_supports_reasoning_extra_body`)

```diff
         if "openrouter" not in self._base_url_lower:
             return False
+        # [PATCH] TokenRouter: forward reasoning_effort to M3
+        if base_url_host_matches(self._base_url_lower, "api.tokenrouter.com"):
+            if "minimax" in (self.model or "").lower() or "m3" in (self.model or "").lower():
+                return True
+            return False
         if "api.mistral.ai" in self._base_url_lower:
             return False
```

## Patch #2: Use `reasoning_effort` field name for TokenRouter

**File:** `run_agent.py` line ~11950-11957

```diff
             if not _is_lmstudio_summary and self._supports_reasoning_extra_body():
                 if self.reasoning_config is not None:
-                    summary_extra_body["reasoning"] = self.reasoning_config
+                    # [PATCH] TokenRouter expects `reasoning_effort` at top level
+                    if base_url_host_matches(self._base_url_lower, "api.tokenrouter.com"):
+                        summary_kwargs["reasoning_effort"] = self.reasoning_config
+                    else:
+                        summary_extra_body["reasoning"] = self.reasoning_config
                 else:
                     summary_extra_body["reasoning"] = {
                         "enabled": True,
                         "effort": "medium"
                     }
```

**⚠️ Note:** Patch #2 may not work cleanly because `summary_kwargs` is built AFTER `summary_extra_body` in the code. Need to verify line order. If conflict, alternative is to also add to `summary_extra_body` as `reasoning_effort` (TokenRouter M3 may accept both).

## Patch #3: Add opt-in config flag

**File:** `config.yaml` line ~3 (under `model:`)

```diff
 model:
   default: MiniMax-M3
   provider: custom
   base_url: https://api.tokenrouter.com/v1
   api_key: sk-Ty6...n2Ae
+  # [PATCH] Enable reasoning_effort auto-forward to M3
+  # Levels: "none" | "low" | "medium" | "high" | "" (off)
+  # When set, Hermes injects this into every M3 API call
+  reasoning_effort: ""
```

---

## Alternative (simpler): Skip patch, use `auto_reasoning.py` directly

**For ad-hoc:**
```bash
python3 ~/.hermes/scripts/auto_reasoning.py "your prompt"
```

**For crons:** Restructure [[Cron]] to call auto_reasoning.py first, then use result in Hermes prompt.
- Pros: No patch, no risk, opt-in per cron
- Cons: Cron becomes 2-step (script + Hermes with answer)

---

## Rollback procedure

```bash
# 1. Restore backup
cp /usr/local/lib/python3.14/dist-packages/run_agent.py.bak.<timestamp> \
   /usr/local/lib/python3.14/dist-packages/run_agent.py

# 2. Remove config flag
# Edit ~/.hermes/config.yaml — delete the reasoning_effort: "" line

# 3. Restart Hermes (if running gateway)
hermes gateway restart
```

## Risk assessment

| Risk | Level | Mitigation |
|---|---|---|
| Patch breaks M3 calls | Medium | Backup + opt-in flag = safe to disable |
| Hermes update overwrites patch | High | Re-apply after each update OR use alternative |
| Affects other models on same provider | Low | Patch only matches `minimax`/`m3` in model name |
| Unknown side effect | Medium | Limited blast radius (TokenRouter + M3 only) |
