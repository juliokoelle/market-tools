"""
Morning push: sends a daily task summary to Telegram at 08:30.

Reads today's Daily Note from GitHub (julio-brain), extracts open tasks
and follow-ups, and sends a formatted Telegram message.
Also checks 50_People/ for upcoming birthdays (today + next 7 days).
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import requests

from scripts.sync_to_brain import _gh_config, github_read
from scripts.utils import today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
_OWNER_ID = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_OWNER_ID", "")
_BERLIN   = ZoneInfo("Europe/Berlin")

_SEND_URL = f"https://api.telegram.org/bot{_TOKEN}/sendMessage"

SECTIONS_TO_SHOW = ["Tasks", "Follow-ups"]
TASK_LIMIT = 10


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


def _parse_birthday(value: str) -> tuple[int, int] | None:
    """Parse birthday field into (month, day). Accepts YYYY-MM-DD or MM-DD."""
    value = value.strip()
    parts = value.split("-")
    try:
        if len(parts) == 3:
            return int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def _extract_frontmatter_birthday(text: str) -> str | None:
    """Extract 'birthday:' value from YAML frontmatter (between --- markers)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            break
        if line.startswith("birthday:"):
            return line[len("birthday:"):].strip()
    return None


def _list_github_directory(path: str) -> list[str]:
    """List filenames in a GitHub repo directory. Returns list of filenames."""
    cfg = _gh_config()
    if not cfg:
        log.warning("[birthday] GITHUB_TOKEN not set — cannot list directory.")
        return []
    token, owner, repo = cfg
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list):
                return [item["name"] for item in items if item.get("type") == "file"]
        elif resp.status_code != 404:
            log.warning("[birthday] GitHub directory list HTTP %s for %s", resp.status_code, path)
    except requests.RequestException as e:
        log.warning("[birthday] GitHub directory list failed: %s", e)
    return []


def _check_birthdays() -> list[str]:
    """
    Scan all files in 50_People/ for birthday fields.
    Returns list of formatted strings for people with birthdays today or in next 7 days.
    """
    today_date = date.today()
    upcoming: list[tuple[int, str]] = []

    filenames = _list_github_directory("50_People")
    log.info("[birthday] Found %d files in 50_People/", len(filenames))

    for filename in filenames:
        if not filename.endswith(".md"):
            continue
        path = f"50_People/{filename}"
        text = github_read(path)
        if not text:
            continue
        bday_val = _extract_frontmatter_birthday(text)
        if not bday_val:
            continue
        parsed = _parse_birthday(bday_val)
        if not parsed:
            log.warning("[birthday] Could not parse birthday '%s' in %s", bday_val, filename)
            continue
        month, day = parsed

        name = filename[:-3].replace("-", " ").title()

        current_year = today_date.year
        try:
            bday_this_year = date(current_year, month, day)
        except ValueError:
            log.warning("[birthday] Invalid date %d-%d in %s", month, day, filename)
            continue

        if bday_this_year < today_date:
            try:
                bday_this_year = date(current_year + 1, month, day)
            except ValueError:
                continue

        days_until = (bday_this_year - today_date).days

        if 0 <= days_until <= 7:
            if days_until == 0:
                msg = f"🎂 *{name}* hat heute Geburtstag!"
            elif days_until == 1:
                msg = f"🎁 *{name}* hat morgen Geburtstag ({bday_this_year.strftime('%-d. %B')})"
            else:
                msg = f"🎁 *{name}* hat in {days_until} Tagen Geburtstag ({bday_this_year.strftime('%-d. %B')})"
            upcoming.append((days_until, msg))
            log.info("[birthday] %s", msg)

    upcoming.sort(key=lambda x: x[0])
    return [msg for _, msg in upcoming]


def _build_message(
    run_date: str,
    tasks: list[str],
    followups: list[str],
    birthdays: list[str],
    subtitle: str = "",
) -> str:
    now = datetime.now(tz=_BERLIN)
    day_str = now.strftime("%-d. %B %Y")

    lines = [
        f"☀️ *Guten Morgen!*",
        f"📅 *{day_str}*",
        "",
    ]
    if subtitle:
        lines += [f"_{subtitle}_", ""]

    # Tasks section
    lines.append("📋 *Tasks*")
    if tasks:
        shown = tasks[:TASK_LIMIT]
        for t in shown:
            lines.append(f"• {t}")
        if len(tasks) > TASK_LIMIT:
            lines.append(f"_(+{len(tasks) - TASK_LIMIT} weitere)_")
    else:
        lines.append("Nichts offen ✅")

    # Follow-ups section
    lines.append("")
    lines.append("⏰ *Follow-ups*")
    if followups:
        for f in followups:
            lines.append(f"• {f}")
    else:
        lines.append("Keine ✅")

    # Birthdays section (only if any)
    if birthdays:
        lines.append("")
        lines.append("🎂 *Geburtstage*")
        for b in birthdays:
            lines.append(b)

    return "\n".join(lines)


def send_morning_push() -> None:
    if not _TOKEN or not _OWNER_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or TELEGRAM_OWNER_ID) must be set"
        )

    run_date = today()
    log.info("Morning push for %s", run_date)

    text = github_read(f"10_Daily/{run_date}.md")
    birthdays = _check_birthdays()

    if text is None:
        log.warning("No daily note found for %s — trying yesterday", run_date)
        yesterday = (date.fromisoformat(run_date) - timedelta(days=1)).isoformat()
        yesterday_text = github_read(f"10_Daily/{yesterday}.md") or ""
        now = datetime.now(tz=_BERLIN)
        day_str = now.strftime("%-d. %B %Y")
        if yesterday_text:
            tasks = _extract_open(yesterday_text, "Tasks")
            followups = _extract_open(yesterday_text, "Follow-ups")
            if tasks or followups:
                message = _build_message(
                    run_date, tasks, followups, birthdays,
                    subtitle=f"Noch keine heutige Note — offene Tasks von {yesterday}",
                )
            else:
                message = (
                    f"☀️ *Guten Morgen!*\n📅 *{day_str}*\n\n"
                    "Keine offenen Tasks — gestern alles erledigt ✅"
                )
                if birthdays:
                    message += "\n\n🎂 *Geburtstage*\n" + "\n".join(birthdays)
        else:
            message = (
                f"☀️ *Guten Morgen!*\n📅 *{day_str}*\n\n"
                "Noch keine Daily Note für heute — sie wird in Kürze erstellt."
            )
            if birthdays:
                message += "\n\n🎂 *Geburtstage*\n" + "\n".join(birthdays)
    else:
        tasks     = _extract_open(text, "Tasks")
        followups = _extract_open(text, "Follow-ups")
        message   = _build_message(run_date, tasks, followups, birthdays)

    resp = httpx.post(_SEND_URL, json={
        "chat_id": _OWNER_ID,
        "text": message,
        "parse_mode": "Markdown",
    }, timeout=10)
    resp.raise_for_status()
    log.info("Morning push sent OK")


if __name__ == "__main__":
    send_morning_push()
