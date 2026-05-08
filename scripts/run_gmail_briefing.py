"""
Gmail briefing pipeline — designed to run as a Render Cron Job at 06:15 UTC.

Steps:
  1. Verify GMAIL_USERNAME and GMAIL_APP_PASSWORD are set
  2. Fetch today's newsletters from Gmail via IMAP
  3. Save to outputs/latest-briefing.md + outputs/YYYY-MM-DD-briefing.md
  4. Sync to julio-brain via GitHub API

Run locally:
    python -m scripts.run_gmail_briefing

Required environment variables:
    GMAIL_USERNAME
    GMAIL_APP_PASSWORD
    GITHUB_TOKEN           (for sync_to_brain)
    JULIO_BRAIN_OWNER      (default: juliokoelle)
    JULIO_BRAIN_REPO_NAME  (default: julio-brain)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from scripts.fetch_gmail_briefing import fetch_today_briefing  # noqa: E402
from scripts.sync_to_brain import sync as brain_sync           # noqa: E402
from scripts.utils import today                                 # noqa: E402

OUTPUTS_DIR = Path("outputs")
LATEST_FILE = OUTPUTS_DIR / "latest-briefing.md"


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def _check_env() -> None:
    missing = [v for v in ("GMAIL_USERNAME", "GMAIL_APP_PASSWORD") if not os.getenv(v)]
    if missing:
        _log(f"ERROR — missing env vars: {', '.join(missing)}")
        sys.exit(1)


def run() -> None:
    _check_env()

    run_date = today()
    _log(f"=== Gmail briefing pipeline started for {run_date} ===")

    _log("Fetching emails from Gmail…")
    briefing_md = fetch_today_briefing()

    if briefing_md is None:
        _log("No briefing emails found today — exiting without overwrite.")
        sys.exit(0)

    header  = f"# Daily Briefing — {run_date}\n\n"
    content = header + briefing_md

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_FILE.write_text(content, encoding="utf-8")
    _log(f"Saved latest  → {LATEST_FILE}")

    archive = OUTPUTS_DIR / f"{run_date}-briefing.md"
    archive.write_text(content, encoding="utf-8")
    _log(f"Saved archive → {archive}")

    try:
        brain_sync(run_date, content)
        _log("Synced to julio-brain.")
    except Exception as e:
        _log(f"Brain sync failed (non-blocking): {e}")

    _log("=== Pipeline complete. ===")


if __name__ == "__main__":
    run()
