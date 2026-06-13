#!/usr/bin/env python3
"""
ftscraper_cron.py - Scheduled FTScraper runner

Runs FTScraper.py on configured URLs, logs results, alerts on failure.

Features:
- Multiple URL rotation (round-robin)
- Per-URL state tracking
- Failure detection (HTTP errors, empty responses, timeouts)
- Output archive with timestamp
- Summary statistics (avg latency, success rate)
- Dry-run mode for testing

Env config:
  FTSCRAPER_URLS=url1,url2,url3  (comma-separated)
  FTSCRAPER_TIMEOUT=30
  FTSCRAPER_MAX_RETRIES=2
  FTSCRAPER_ARCHIVE_DIR=~/.hermes/notes/scraper-archive
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / ".hermes"
FTSCRAPER = "/root/ft-data-pipeline/FTScraper.py"
DEFAULT_URLS = [
    "https://example.com",
    "https://nowsecure.nl",
    "https://httpbin.org/html",
]
STATE_FILE = HERMES / "logs" / "ftscraper-state.json"
LOG_FILE = HERMES / "logs" / "ftscraper-runs.jsonl"
ARCHIVE_DIR = Path(os.environ.get("FTSCRAPER_ARCHIVE_DIR", HERMES / "notes" / "scraper-archive"))

URLS = os.environ.get("FTSCRAPER_URLS", ",".join(DEFAULT_URLS)).split(",")
TIMEOUT = int(os.environ.get("FTSCRAPER_TIMEOUT", "30"))
MAX_RETRIES = int(os.environ.get("FTSCRAPER_MAX_RETRIES", "2"))


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_index": -1, "history": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def pick_next_url(state):
    state["last_index"] = (state["last_index"] + 1) % len(URLS)
    return URLS[state["last_index"]]


def run_scraper(url, dry_run=False):
    """Run FTScraper.py on URL. Returns (success, latency_s, output_size, error)."""
    start = time.perf_counter()
    cmd = ["python3", FTSCRAPER, url, "--timeout", str(TIMEOUT)]
    if dry_run:
        cmd.append("--dry-run")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT + 10)
        elapsed = time.perf_counter() - start
        success = r.returncode == 0 and r.stdout.strip() and "ERROR" not in r.stdout
        return success, elapsed, len(r.stdout), r.stderr[:200] if r.stderr else ""
    except subprocess.TimeoutExpired:
        return False, time.perf_counter() - start, 0, "TIMEOUT"
    except Exception as e:
        return False, time.perf_counter() - start, 0, str(e)[:200]


def archive_output(url, output, timestamp):
    """Save successful scrape to archive with metadata."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    safe_url = url.replace("/", "_").replace(":", "")[:60]
    archive_file = ARCHIVE_DIR / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{safe_url}.json"
    archive_file.write_text(json.dumps({
        "url": url,
        "timestamp": timestamp.isoformat(),
        "output": output,
    }, indent=2, ensure_ascii=False))
    return archive_file


def main():
    dry_run = "--dry-run" in sys.argv
    state = load_state()
    url = pick_next_url(state)
    now = datetime.now()

    print(f"🕷️  FTScraper Cron — {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"   URL: {url}")
    print(f"   URL pool: {len(URLS)} (rotation index={state['last_index']})")

    if not Path(FTSCRAPER).exists():
        print(f"❌ FTScraper not found at {FTSCRAPER}")
        return 1

    # Run with retries
    success = False
    last_err = ""
    last_size = 0
    last_latency = 0
    for attempt in range(1, MAX_RETRIES + 2):  # initial + retries
        print(f"   Attempt {attempt}/{MAX_RETRIES + 1}...")
        success, latency, size, err = run_scraper(url, dry_run)
        last_err, last_size, last_latency = err, size, latency
        if success:
            break
        if attempt < MAX_RETRIES + 1:
            time.sleep(2)  # backoff

    # Record run
    run = {
        "ts": now.isoformat(),
        "url": url,
        "success": success,
        "latency_s": round(last_latency, 2),
        "output_bytes": last_size,
        "attempts": min(attempt, MAX_RETRIES + 1),
        "error": last_err if not success else None,
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(run) + "\n")

    # Update state history (last 50)
    state["history"] = state.get("history", []) + [run]
    state["history"] = state["history"][-50:]
    save_state(state)

    # Archive successful outputs
    if success and last_size > 0 and not dry_run:
        archive_path = archive_output(url, f"<{last_size} bytes scraped>", now)
        run["archive"] = str(archive_path)

    # Stats
    history = state["history"]
    total = len(history)
    successes = sum(1 for h in history if h.get("success"))
    success_rate = (successes / total * 100) if total else 0
    avg_latency = sum(h.get("latency_s", 0) for h in history) / total if total else 0

    print(f"\n   Result: {'✅' if success else '❌'}")
    print(f"   Latency: {last_latency:.2f}s")
    print(f"   Output: {last_size} bytes")
    if last_err:
        print(f"   Error: {last_err}")
    print(f"\n📊 Stats ({total} runs):")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   Avg latency: {avg_latency:.2f}s")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
