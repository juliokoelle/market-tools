"""
Daily briefing pipeline — designed to run as a Render Cron Job.

Steps:
  1. Fetch fresh market data   (Twelve Data + yfinance + NewsAPI)
  2. Build the structured prompt
  3. Generate the briefing via Anthropic API
  4. Save to outputs/latest-briefing.md  (overwrite — always the latest)
     and   outputs/YYYY-MM-DD-briefing.md  (archive copy)

Run locally:
    python -m scripts.run_daily

Required environment variables:
    ANTHROPIC_API_KEY
    TWELVE_DATA_API_KEY
    NEWS_API_KEY
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY")
TWELVE_DATA_KEY    = os.getenv("TWELVE_DATA_API_KEY")
NEWS_API_KEY_CHECK = os.getenv("NEWS_API_KEY")

MODEL   = "claude-opus-4-6"
# Max tokens for a 5–10 minute read ≈ 2 000–3 000 words ≈ 2 500–4 000 tokens
MAX_TOKENS = 4096

OUTPUTS_DIR   = Path("outputs")
LATEST_FILE   = OUTPUTS_DIR / "latest-briefing.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str):
    """Timestamped stdout logging — visible in Render Cron logs."""
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def _notify_telegram(msg: str) -> None:
    """Send a Telegram message to the owner. Non-blocking — errors are logged only."""
    import requests as _req
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_OWNER_ID", "")
    if not token or not chat_id:
        return
    try:
        _req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
    except Exception as e:
        log(f"Telegram notify failed (non-fatal): {e}")


def check_env():
    missing = [
        name for name, val in [
            ("ANTHROPIC_API_KEY",  ANTHROPIC_API_KEY),
            ("TWELVE_DATA_API_KEY", TWELVE_DATA_KEY),
            ("NEWS_API_KEY",        NEWS_API_KEY_CHECK),
        ]
        if not val
    ]
    if missing:
        log(f"ERROR — missing environment variables: {', '.join(missing)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run():
    check_env()

    from scripts.utils import today, output_path
    from scripts.fetch_data import run as fetch_run
    from scripts.generate_briefing import build_prompt

    run_date = today()
    log(f"=== Daily briefing pipeline started for {run_date} ===")

    # ── Step 1: Fetch data ──────────────────────────────────────────────────
    log("Fetching data…")
    try:
        fetch_run(run_date)
    except Exception as e:
        log(f"ERROR during data fetch: {e}")
        sys.exit(1)
    log("Data fetch complete.")

    # ── Step 2: Build prompt ────────────────────────────────────────────────
    log("Building prompt…")
    try:
        prompt = build_prompt(run_date)
    except Exception as e:
        log(f"ERROR building prompt: {e}")
        sys.exit(1)
    log(f"Prompt ready ({len(prompt)} characters).")

    # ── Step 3: Generate briefing via Anthropic API ─────────────────────────
    log("Generating briefing…")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=(
                "You are a senior economic journalist producing the Daily Global Economic "
                "Newspaper Briefing. Follow all editorial standards exactly as instructed. "
                "Write in continuous journalistic prose. No bullet lists in the final output."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        briefing = message.content[0].text
    except Exception as e:
        log(f"ERROR calling Anthropic API: {e}")
        sys.exit(1)
    log(f"Briefing generated ({len(briefing.split())} words).")

    # ── Step 4: Save output ─────────────────────────────────────────────────
    log("Saving latest briefing…")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    header = f"# Daily Global Economic Briefing — {run_date}\n\n"
    content = header + briefing

    # Always overwrite latest — this is what the API endpoint serves
    LATEST_FILE.write_text(content, encoding="utf-8")
    log(f"Saved latest briefing → {LATEST_FILE}")

    # Archive copy with date in filename
    archive = Path(output_path(run_date))
    archive.write_text(content, encoding="utf-8")
    log(f"Saved archive copy   → {archive}")

    # ── Step 5: Sync to julio-brain ─────────────────────────────────────────
    log("Syncing to julio-brain…")
    sync_ok = False
    try:
        from scripts.sync_to_brain import sync as brain_sync
        brain_sync(run_date, content, path=f"10_Daily/{run_date}-economic.md")
        log("Synced to julio-brain.")
        sync_ok = True
    except Exception as e:
        log(f"Brain sync failed (non-blocking): {e}")

    log("=== Pipeline complete. ===")
    word_count = len(briefing.split())
    if sync_ok:
        _notify_telegram(f"✅ Economic Briefing {run_date} — {word_count} Wörter generiert & in julio-brain gespeichert")
    else:
        _notify_telegram(f"⚠️ Economic Briefing {run_date} — {word_count} Wörter generiert, aber Brain-Sync fehlgeschlagen. Render Logs prüfen.")


if __name__ == "__main__":
    try:
        run()
    except SystemExit as e:
        if e.code and int(e.code) != 0:
            _notify_telegram("❌ Economic Briefing fehlgeschlagen — Render Logs prüfen")
        raise
    except Exception as e:
        _notify_telegram(f"❌ Economic Briefing crashed: {e}")
        raise
