"""
Gmail briefing pipeline — runs as a LaunchAgent (08:15 CEST) or Render Cron (06:15 UTC).

Steps:
  1. Verify GMAIL_USERNAME and GMAIL_APP_PASSWORD are set
  2. Fetch today's newsletters from Gmail via IMAP
  3. Save to outputs/latest-briefing.md + outputs/YYYY-MM-DD-briefing.md
  4. Sync to julio-brain via GitHub API

Run locally (today):
    python -m scripts.run_gmail_briefing

Backfill a specific date:
    python -m scripts.run_gmail_briefing --date 2026-05-11

Backfill a date range:
    for d in 2026-05-11 2026-05-12 2026-05-13; do
        python -m scripts.run_gmail_briefing --date $d; done

Required environment variables:
    GMAIL_USERNAME
    GMAIL_APP_PASSWORD
    GITHUB_TOKEN           (for sync_to_brain)
    JULIO_BRAIN_OWNER      (default: juliokoelle)
    JULIO_BRAIN_REPO_NAME  (default: julio-brain)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests as _requests

from dotenv import load_dotenv

load_dotenv()

from scripts.fetch_gmail_briefing import fetch_today_briefing  # noqa: E402
from scripts.redis_state import heartbeat, install_redis_log_handler  # noqa: E402
from scripts.sync_to_brain import sync as brain_sync           # noqa: E402
from scripts.utils import today                                 # noqa: E402

OUTPUTS_DIR = Path("outputs")
LATEST_FILE = OUTPUTS_DIR / "latest-briefing.md"

_SERVICE = "gmail-briefing"
log = logging.getLogger(_SERVICE)

_GH_TOKEN  = os.getenv("GITHUB_TOKEN", "")
_GH_OWNER  = os.getenv("JULIO_BRAIN_OWNER", "juliokoelle")
_GH_REPO   = os.getenv("JULIO_BRAIN_REPO_NAME", "julio-brain")


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def _notify_telegram(msg: str) -> None:
    """Send a Telegram message to the owner. Non-blocking."""
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_OWNER_ID", "")
    if not token or not chat_id:
        return
    try:
        _requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
    except Exception as e:
        _log(f"Telegram notify failed (non-fatal): {e}")


def _check_env() -> None:
    missing = [v for v in ("GMAIL_USERNAME", "GMAIL_APP_PASSWORD") if not os.getenv(v)]
    if missing:
        _log(f"ERROR — missing env vars: {', '.join(missing)}")
        log.error("missing env vars: %s", ", ".join(missing))
        sys.exit(1)


def _already_synced(run_date: str) -> bool:
    """Return True if today's briefing archive already exists locally — skip re-run."""
    return (OUTPUTS_DIR / f"{run_date}-briefing.md").exists()


def _wait_for_network(max_attempts: int = 6, delay: int = 30) -> bool:
    """Wait until DNS resolves. Returns True when network is up, False on timeout."""
    import socket
    for attempt in range(max_attempts):
        try:
            socket.getaddrinfo("imap.gmail.com", 993)
            return True
        except OSError:
            if attempt < max_attempts - 1:
                _log(f"Network not ready (attempt {attempt + 1}/{max_attempts}), retrying in {delay}s…")
                time.sleep(delay)
    return False


def run(run_date_str: str | None = None) -> None:
    install_redis_log_handler(_SERVICE)  # errors below show up in the bot's /health
    heartbeat(_SERVICE)                  # liveness signal for /health
    _check_env()

    run_date = run_date_str or today()
    _log(f"=== Gmail briefing pipeline started for {run_date} ===")

    # Idempotency: skip if this date is already in GitHub (safe for multiple daily triggers)
    if run_date_str is None and _already_synced(run_date):
        _log(f"Briefing for {run_date} already in julio-brain — skipping.")
        sys.exit(0)

    # Wait for network if DNS is not yet available (common after Mac wake-from-sleep)
    if not _wait_for_network():
        _log("ERROR — network unavailable after retries. Exiting.")
        sys.exit(1)

    # Parse target_date for backfill (ON search) vs today (SINCE yesterday search)
    target: date | None = None
    if run_date_str is not None:
        year, month, day = map(int, run_date_str.split("-"))
        target = date(year, month, day)

    _log("Fetching emails from Gmail…")
    briefing_md = fetch_today_briefing(target_date=target)

    if briefing_md is None:
        _log("No briefing emails found — exiting without overwrite.")
        sys.exit(0)

    header  = f"# Daily Briefing — {run_date}\n\n"
    content = header + briefing_md

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_FILE.write_text(content, encoding="utf-8")
    _log(f"Saved latest  → {LATEST_FILE}")

    archive = OUTPUTS_DIR / f"{run_date}-briefing.md"
    archive.write_text(content, encoding="utf-8")
    _log(f"Saved archive → {archive}")

    sync_ok = False
    try:
        brain_sync(run_date, content)
        _log("Synced to julio-brain.")
        sync_ok = True
    except Exception as e:
        _log(f"Brain sync failed (non-blocking): {e}")
        log.error("brain sync failed: %s", e)

    _log("=== Pipeline complete. ===")
    if sync_ok:
        _notify_telegram(f"✅ Gmail Briefing {run_date} in julio-brain gespeichert")
    else:
        _notify_telegram(f"⚠️ Gmail Briefing {run_date} gespeichert, aber Brain-Sync fehlgeschlagen. Render Logs prüfen.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail briefing pipeline")
    parser.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        default=None,
        help="Target date for backfill (default: today, uses SINCE-yesterday IMAP search)",
    )
    args = parser.parse_args()
    try:
        run(args.date)
    except SystemExit as e:
        if e.code and int(e.code) != 0:
            log.error("pipeline exited with code %s", e.code)
            _notify_telegram("❌ Gmail Briefing fehlgeschlagen — Render Logs prüfen")
        raise
    except Exception as e:
        log.error("pipeline crashed: %s", e)
        _notify_telegram(f"❌ Gmail Briefing crashed: {e}")
        raise
