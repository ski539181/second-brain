# Extended Notes — Index

This is the **extended memory** layer. Lives outside the main memory budget.
Main memory only stores a pointer to this file; everything else goes here.

## 🚀 Quick Start (for new models)

**Read `STATE.md` first** — it's a 1-read handoff doc with full system context.
Then come back here for the file index.

## 📂 Files

### Core
- `notes.md` — Second Brain (projects, ideas, opportunities)
- `STATE.md` — **handoff doc** (system state, cron jobs, gotchas, quick searches)
- `cron-decisions.md` — feedback log (auto-created, tracks ✅/❌ from user)
- `cross.md` — **AI rules** (Second Brain schema — read before processing files)
- `podcast.md` — **session summary log** (5-10 bullets/session, save tokens)
- `raw/README.md` — raw inputs structure (read-only, no edits by AI)
- `ai-knowledge.md` — Karpathy 17 insights (10 actionable rules for LLM use)
- `tokenrouter-reasoning.md` — M3 + TokenRouter `reasoning_effort` API support (verified)

### Web Scraper FT Dataset (temporary — ลบเมื่อ FT เสร็จ)
- `scraper-cheatsheet.md` — quick formulas/patterns
- `scraper-antipatterns.md` — what NOT to do
- `scraper-decision-tree.md` — when to do what
- `scraper-checklist.md` — pre-deploy verification
- `scraper-snippets.md` — copy-paste code (20 snippets)

## When to grep this folder

Check files (via `search_files pattern=...`) when a topic might have
prior context. Triggers:

- **User setup / config** (TokenRouter, providers, models)
- **Hermes / CLI behavior** gotchas
- **Past troubleshooting** that could repeat
- **Recurring project info**
- **Cron jobs** (read STATE.md first)
- **Web scraper** (load skill `web-scraper-expert` OR grep scraper-* files)
- Anything the user says "จำไว้" / "remember this" that's **reference**, not
  always-needed preference.

Do **not** auto-inject these files into context. Grep on demand only.

## How to grep

```python
search_files(pattern="keyword", path="~/.hermes/notes", target="content")
```

Ripgrep — fast, returns matching lines with line numbers. If a section grows
past ~5k chars, consider splitting into its own file.

## How to add notes

When user shares a durable fact and main memory is the wrong place:

1. Open `notes.md`, find the right `## Section`.
2. Append a bullet. Keep entries terse, dated when relevant.
3. If the topic is brand new, add a new `## Section` header.

## What does NOT go here

- Always-needed preferences (language, terse, opt-in rule) — main `user` memory.
- Tool quirks that are environment-stable — main `memory`.
- One-off task state — never memory, use `session_search` for past sessions.
- System state (cron, skills, gotchas) — `STATE.md` (this handoff doc).

## When to update STATE.md

Update `STATE.md` when:
- New cron job created/removed
- New skill added/removed
- New project starts/ends
- New gotcha discovered
- File map changes

Keep it under 3 KB. Bullet points only. No prose.
