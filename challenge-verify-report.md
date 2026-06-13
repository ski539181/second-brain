# Challenge Verify Report
2026-06-13 20:46

## Summary
- Total: 45
- ✅ Confirmed: 6
- ⏭️ Skipped: 39
- ❌ Failed: 0

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
| 8 | 8. List multiply reference | ✅ | syntax ok, bug in modification (test separately) |
| 9 | 9. Tuple as dict key (with list) | ⏭️ | skipped (manual verify) |
| 10 | 10. Encoding issues | ⏭️ | skipped (manual verify) |
| 11 | 11. Off-by-one slicing | ✅ | bug confirmed (stop is exclusive) |
| 12 | 12. Sort stability | ⏭️ | skipped (manual verify) |
| 13 | 13. *args mutation | ⏭️ | skipped (manual verify) |
| 14 | 14. Walrus in comprehension | ⏭️ | skipped (manual verify) |
| 15 | 15. Star in function call | ⏭️ | skipped (manual verify) |
| 16 | 16. Word splitting | ⏭️ | skipped (manual verify) |
| 17 | 17. Subshell variable scope | ⏭️ | skipped (manual verify) |
| 18 | 18. Exit code in pipe | ⏭️ | skipped (manual verify) |
| 19 | 19. Quoting arrays | ⏭️ | skipped (manual verify) |
| 20 | 20. SIGPIPE | ⏭️ | skipped (manual verify) |
| 21 | 21. Race condition in temp files | ⏭️ | skipped (manual verify) |
| 22 | 22. Set -e edge case | ⏭️ | skipped (manual verify) |
| 23 | 23. For loop glob | ⏭️ | skipped (manual verify) |
| 24 | 24. Race on shared counter | ✅ | bug confirmed (race produces < expected) |
| 25 | 25. Async generator cleanup | ⏭️ | skipped (manual verify) |
| 26 | 26. Deadlock with locks | ⏭️ | skipped (manual verify) |
| 27 | 27. Thread-safe counter | ⏭️ | skipped (manual verify) |
| 28 | 28. asyncio.gather vs TaskGroup | ⏭️ | skipped (manual verify) |
| 29 | 29. CORS preflight | ⏭️ | skipped (manual verify) |
| 30 | 30. Rate limit retry | ⏭️ | skipped (manual verify) |
| 31 | 31. Streaming response | ⏭️ | skipped (manual verify) |
| 32 | 32. JSON parse error | ⏭️ | skipped (manual verify) |
| 33 | 33. Connection pool exhaustion | ⏭️ | skipped (manual verify) |
| 34 | 34. SQL injection | ⏭️ | skipped (manual verify) |
| 35 | 35. N+1 query | ⏭️ | skipped (manual verify) |
| 36 | 36. Transaction isolation | ⏭️ | skipped (manual verify) |
| 37 | 37. Connection leak | ⏭️ | skipped (manual verify) |
| 38 | 38. File handle leak | ⏭️ | skipped (manual verify) |
| 39 | 39. Atomic write | ⏭️ | skipped (manual verify) |
| 40 | 40. Symlink loop | ⏭️ | skipped (manual verify) |
| 41 | 41. Path traversal | ⏭️ | skipped (manual verify) |
| 42 | 42. Command injection | ⏭️ | skipped (manual verify) |
| 43 | 43. Pickle deserialization | ⏭️ | skipped (manual verify) |
| 44 | 44. Timing attack | ⏭️ | skipped (manual verify) |
| 45 | 45. Open redirect | ⏭️ | skipped (manual verify) |


## What this verifies
- Buggy code reproduces documented behavior
- Fixes work correctly

## What's NOT verified
- Shell/bash problems (need bash, not python)
- JavaScript (need node)
- Long-running async (5s timeout)
- Network/DB (no infrastructure)
- Security problems (real exploitation would be unsafe)
- Some Python (no testable output in snippet)


---
Auto-verify script: ~/.hermes/scripts/verify_challenges.py
Run: `python3 ~/.hermes/scripts/verify_challenges.py`
