# Pending Security Items (2026-06-13)

## 🚨 Revoke GitHub tokens (paste'd in chat)

**2 tokens were shared in chat earlier in the session:**

1. `github_pat_...F8oP...` (paste 1) — failed with 403
2. `github_pat_...jNEZ...` (paste 2) — used for ft-data-pipeline push (commit 0183f28)

**Action:** Revoke at https://github.com/settings/tokens

**Also revoke if any other test tokens were created during the session.**

## 🔑 Active credentials (safe)

- `~/.gitconfig` has ski539181's fine-grained PAT (x-access-token) — used for second-brain push
- This is in `.git/config` URL, so it's still functional

## Recommendations

1. Use **GitHub App tokens** instead of PATs (more granular, time-limited)
2. Set **expiry date** on all PATs
3. Use **different tokens** for different scopes (read vs write)
4. Never paste tokens in chat (always use credential_pool or env vars)
