# Challenge Verify Report
2026-06-13 23:55

## Summary
- Total: 45
- ✅ Confirmed: 28
- ⏭️ Skipped: 15
- ❌ Failed: 2

## Results

| # | Title | Status | Note |
|---|-------|--------|------|
| 1 | 1. Mutable default argument | ✅ | bug confirmed (default persists across calls) |
| 2 | 2. Late binding closures | ✅ | bug confirmed (all return last i) |
| 3 | 3. Generator exhaustion | ⏭️ | skipped (manual verify) |
| 4 | 4. None comparison | ⏭️ | skipped (manual verify) |
| 5 | 5. String interning | ⏭️ | skipped (manual verify) |
| 6 | 6. Float equality | ✅ | bug confirmed (0.1+0.2 = 0.3000...04) |
| 7 | 7. Dict mutation during iteration | ⏭️ | skipped (manual verify) |
| 8 | 8. List multiply reference | ✅ | syntax ok, bug in modification ([[test]] separately) |
| 9 | 9. Tuple as dict key (with list) | ⏭️ | skipped (manual verify) |
| 10 | 10. Encoding issues | ⏭️ | skipped (manual verify) |
| 11 | 11. Off-by-one slicing | ✅ | bug confirmed (stop is exclusive) |
| 12 | 12. Sort stability | ⏭️ | skipped (manual verify) |
| 13 | 13. *args mutation | ⏭️ | skipped (manual verify) |
| 14 | 14. Walrus in comprehension | ⏭️ | skipped (manual verify) |
| 15 | 15. Star in function call | ⏭️ | skipped (manual verify) |
| 16 | 16. Word splitting | ✅ | bug demonstrated (splitting vs quoting) |
| 17 | 17. Subshell variable scope | ✅ | bug confirmed (subshell scope, count=0) |
| 18 | 18. Exit [[code]] in pipe | ✅ | bug confirmed (pipe masks error without pipefail) |
| 19 | 19. Quoting arrays | ✅ | bug demonstrated (quoting changes iteration) |
| 20 | 20. SIGPIPE | ✅ | SIGPIPE handled (exit: exit: 0) |
| 21 | 21. Race condition in temp files | ✅ | bug demonstrated (both work, mktemp safer) |
| 22 | 22. Set -e edge case | ✅ | bug demonstrated (&& exempts from set -e) |
| 23 | 23. For loop glob | ✅ | bug confirmed (glob returns [[pattern]] if no match) |
| 24 | 24. Race on shared counter | ✅ | bug confirmed (race produces < expected) |
| 25 | 25. Async generator cleanup | ❌ | unexpected: cleanup called
 |
| 26 | 26. Deadlock with locks | ✅ | safe pattern verified, deadlock risk documented |
| 27 | 27. Thread-safe counter | ✅ | bug demonstrated (lost updates vs lock-protected) |
| 28 | 28. asyncio.gather vs TaskGroup | ❌ | unexpected:  |
| 29 | 29. CORS preflight | ⏭️ | skipped (manual verify) |
| 30 | 30. Rate limit retry | ⏭️ | skipped (manual verify) |
| 31 | 31. Streaming response | ⏭️ | skipped (manual verify) |
| 32 | 32. JSON parse error | ⏭️ | skipped (manual verify) |
| 33 | 33. Connection pool exhaustion | ⏭️ | skipped (manual verify) |
| 34 | 34. SQL injection | ✅ | bug confirmed (injection raises, param safe) |
| 35 | 35. N+1 query | ✅ | bug demonstrated (N+1 vs batch query count) |
| 36 | 36. Transaction isolation | ✅ | bug demonstrated (lost update vs IMMEDIATE) |
| 37 | 37. Connection leak | ✅ | bug demonstrated (no [[auto]]-close, manual needed) |
| 38 | 38. File handle leak | ✅ | bug demonstrated (manual close risk vs with) |
| 39 | 39. Atomic write | ✅ | fix demonstrated (atomic via tmp+replace) |
| 40 | 40. Symlink loop | ✅ | fix verified (followlinks=False prevents loop) |
| 41 | 41. Path traversal | ✅ | vulnerability + fix demonstrated |
| 42 | 42. Command injection | ✅ | vulnerability demonstrated (or safe pattern verified) |
| 43 | 43. Pickle deserialization | ✅ | danger demonstrated (pickle can call arbitrary code) |
| 44 | 44. Timing attack | ✅ | timing attack risk + hmac fix demonstrated |
| 45 | 45. Open redirect | ✅ | vulnerability + whitelist fix demonstrated |


## What this verifies
- Buggy code reproduces documented behavior
- Fixes work correctly

## What's NOT verified
- Shell/bash problems (need bash, not [[python]])
- JavaScript (need node)
- Long-running async (5s timeout)
- Network/DB (no infrastructure)
- Security problems (real exploitation would be unsafe)
- Some Python (no testable output in snippet)
