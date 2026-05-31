"""
Morning push: sends a daily task summary to Telegram at 08:30.

Reads today's Daily Note from GitHub (julio-brain), extracts open tasks
and follow-ups, and sends a formatted Telegram message.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from scripts.sync_to_brain import github_read
from scripts.utils import today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
_OWNER_ID = os.getenv("TELEGRAM_CHAT_ID", "")
_BERLIN   = ZoneInfo("Europe/Berlin")

_SEND_URL = f"https://api.telegram.org/bot{_TOKEN}/sendMessage"

SECTIONS_TO_SHOW = ["Tasks", "Follow-ups"]


def _extract_open(text: str, section: str) -> list[str]:
    lines = text.splitlines()
    header = f"## {section}"
    try:
        start = next(i for i, l in enumerate(lines) if l.rstrip() == header)
    except StopIteration:
        return []
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return [l.strip()[6:] for l in lines[start:end] if l.strip().startswith("- [ ]")]


def _build_message(run_date: str, tasks: list[str], followups: list[str]) -> str:
    now = datetime.now(tz=_BERLIN)
    day_str = now.strftime("%-d. %B %Y")

    lines = [f"☀️ *Guten Morgen!* {day_str}", ""]

    if tasks:
        lines.append(f"📋 *{len(tasks)} offene Task{'s' if len(tasks) != 1 else ''}:*")
        for t in tasks[:5]:
            lines.append(f"• {t}")
        if len(tasks) > 5:
            lines.append(f"_(+{len(tasks) - 5} weitere)_")
    else:
        lines.append("📋 *Tasks:* Nichts offen ✅")

    if followups:
        lines.append("")
        lines.append(f"⏰ *{len(followups)} Follow-up{'s' if len(followups) != 1 else ''}:*")
        for f in followups[:3]:
            lines.append(f"• {f}")

    return "\n".join(lines)


def send_morning_push() -> None:
    if not _TOKEN or not _OWNER_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

    run_date = today()
    log.info("Morning push for %s", run_date)

    text = github_read(f"10_Daily/{run_date}.md") or ""
    if not text:
        log.warning("No daily note found for %s — sending fallback", run_date)
        message = "☀️ *Guten Morgen!*\n\n_Noch keine Daily Note für heute. Tippe /task um zu starten._"
    else:
        tasks    = _extract_open(text, "Tasks")
        followups = _extract_open(text, "Follow-ups")
        message  = _build_message(run_date, tasks, followups)

    resp = httpx.post(_SEND_URL, json={
        "chat_id": _OWNER_ID,
        "text": message,
        "parse_mode": "Markdown",
    }, timeout=10)
    resp.raise_for_status()
    log.info("Morning push sent OK")


if __name__ == "__main__":
    send_morning_push()
