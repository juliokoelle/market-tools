"""
Proactive Intelligence — Julio's second brain daily hint engine.

Runs daily, reads notes and context from julio-brain (GitHub), and sends
1-2 specific, actionable insights via Telegram if anything urgent is found.

Steps:
1. Read last 7 daily notes from 10_Daily/YYYY-MM-DD.md
2. List and read all files in 50_People/ (birthdays, gift ideas)
3. Read 40_Knowledge/open-questions.md
4. Read 00_Inbox/OPEN_TASKS.md if it exists
5. Build a structured context summary
6. Ask Claude Sonnet (claude-sonnet-4-6) for 1-2 actionable insights
7. If Claude returns a non-empty response, send via Telegram
8. If nothing actionable: exit silently

ENV VARS:
  ANTHROPIC_API_KEY
  GITHUB_TOKEN  (or BRAIN_GITHUB_TOKEN as fallback)
  JULIO_BRAIN_OWNER
  JULIO_BRAIN_REPO_NAME
  TELEGRAM_BOT_TOKEN
  TELEGRAM_OWNER_ID
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import anthropic
import requests

from scripts.telegram_utils import send_message
from scripts.utils import today

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

_BERLIN = ZoneInfo("Europe/Berlin")

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _gh_token() -> str:
    """Return GitHub token — prefers GITHUB_TOKEN, falls back to BRAIN_GITHUB_TOKEN."""
    return (
        os.getenv("GITHUB_TOKEN", "").strip()
        or os.getenv("BRAIN_GITHUB_TOKEN", "").strip()
    )


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_gh_token()}",
        "Accept": "application/vnd.github.v3+json",
    }


def _gh_base() -> str:
    owner = os.getenv("JULIO_BRAIN_OWNER", "juliokoelle").strip()
    repo  = os.getenv("JULIO_BRAIN_REPO_NAME", "julio-brain").strip()
    return f"https://api.github.com/repos/{owner}/{repo}/contents"


# ---------------------------------------------------------------------------
# GitHub read helpers
# ---------------------------------------------------------------------------

def _gh_read_file(path: str) -> str | None:
    """Read a single file from GitHub. Returns decoded text or None on failure."""
    if not _gh_token():
        log.warning("[pi] GITHUB_TOKEN not set — skipping read of %s", path)
        return None
    url = f"{_gh_base()}/{path}"
    try:
        resp = requests.get(url, headers=_gh_headers(), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            raw_b64 = data.get("content", "").replace("\n", "")
            return base64.b64decode(raw_b64).decode("utf-8")
        if resp.status_code != 404:
            log.warning("[pi] GitHub GET %s → HTTP %s", path, resp.status_code)
        return None
    except requests.RequestException as exc:
        log.warning("[pi] GitHub read failed for %s: %s", path, exc)
        return None


def _gh_list_dir(path: str) -> list[dict] | None:
    """List directory contents from GitHub. Returns list of file metadata or None."""
    if not _gh_token():
        log.warning("[pi] GITHUB_TOKEN not set — skipping list of %s", path)
        return None
    url = f"{_gh_base()}/{path}"
    try:
        resp = requests.get(url, headers=_gh_headers(), timeout=10)
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list):
                return items
            return None
        if resp.status_code != 404:
            log.warning("[pi] GitHub LIST %s → HTTP %s", path, resp.status_code)
        return None
    except requests.RequestException as exc:
        log.warning("[pi] GitHub list failed for %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# Context gathering
# ---------------------------------------------------------------------------

def _collect_daily_notes(today_str: str, count: int = 7) -> str:
    """Read up to `count` daily notes ending at today. Returns combined text."""
    today_date = date.fromisoformat(today_str)
    parts: list[str] = []
    for delta in range(count):
        note_date = today_date - timedelta(days=delta)
        path = f"10_Daily/{note_date.isoformat()}.md"
        text = _gh_read_file(path)
        if text:
            parts.append(f"### Daily Note {note_date.isoformat()}\n\n{text.strip()}")
            log.info("[pi] Read daily note %s", note_date.isoformat())
        else:
            log.info("[pi] No daily note for %s", note_date.isoformat())
    if not parts:
        return ""
    return "\n\n---\n\n".join(parts)


def _collect_people() -> str:
    """Read all files in 50_People/ and return combined text."""
    items = _gh_list_dir("50_People")
    if not items:
        log.info("[pi] 50_People/ not found or empty")
        return ""

    parts: list[str] = []
    for item in items:
        if item.get("type") != "file":
            continue
        name = item.get("name", "")
        if not name.endswith(".md"):
            continue
        path = item.get("path", f"50_People/{name}")
        text = _gh_read_file(path)
        if text:
            display_name = name.replace(".md", "").replace("-", " ")
            parts.append(f"### Person: {display_name}\n\n{text.strip()}")
            log.info("[pi] Read people file %s", name)

    if not parts:
        return ""
    return "\n\n---\n\n".join(parts)


def _collect_open_questions() -> str:
    text = _gh_read_file("40_Knowledge/open-questions.md")
    if text:
        log.info("[pi] Read open-questions.md")
        return text.strip()
    return ""


def _collect_open_tasks() -> str:
    text = _gh_read_file("00_Inbox/OPEN_TASKS.md")
    if text:
        log.info("[pi] Read OPEN_TASKS.md")
        return text.strip()
    return ""


def _build_context(today_str: str) -> str:
    """Gather all context and assemble into a structured summary string."""
    sections: list[str] = []

    daily = _collect_daily_notes(today_str)
    if daily:
        sections.append(f"## Last 7 Daily Notes\n\n{daily}")
    else:
        sections.append("## Last 7 Daily Notes\n\n_(none found)_")

    people = _collect_people()
    if people:
        sections.append(f"## People (50_People/)\n\n{people}")
    else:
        sections.append("## People (50_People/)\n\n_(none found)_")

    questions = _collect_open_questions()
    if questions:
        sections.append(f"## Open Questions (40_Knowledge/open-questions.md)\n\n{questions}")
    else:
        sections.append("## Open Questions\n\n_(none found)_")

    tasks = _collect_open_tasks()
    if tasks:
        sections.append(f"## Open Tasks (00_Inbox/OPEN_TASKS.md)\n\n{tasks}")

    return "\n\n---\n\n".join(sections)


# ---------------------------------------------------------------------------
# Claude call
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are Julio's second brain. Julio is a German entrepreneur managing 14 car inspection \
stations and a real estate portfolio of 300 apartments. Review his notes, tasks, and people \
context. Identify 1-2 specific, time-sensitive insights he should act on NOW.

Focus on:
- Connections between things (e.g. upcoming trip mentioned + passport expiry mentioned → \
"Renew passport before Brazil trip")
- Upcoming birthdays in the next 14 days
- Tasks or questions that have been open for >7 days without progress
- Things mentioned in notes that have implied deadlines

Rules:
- Be SPECIFIC. Name exact people, dates, tasks.
- Only flag things that are actionable in the next 14 days
- Return null/empty if nothing urgent
- Maximum 2 items
- If returning items, format as a clean Telegram message starting with "🧠 *Second Brain Hint:*"
- Do NOT be generic. "You have open tasks" is bad. \
"Your question about Bonn expansion site has been open 9 days — \
you mentioned a meeting with Paul Haltof next week" is good.\
"""


def _ask_claude(today_str: str, context: str) -> str:
    """Send context to Claude Sonnet and return its response (empty string if nothing urgent)."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    user_message = f"Today is {today_str}. Here is Julio's context:\n\n{context}"

    log.info("[pi] Calling Claude Sonnet for proactive insights…")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response = message.content[0].text.strip() if message.content else ""
    log.info("[pi] Claude response length: %d chars", len(response))
    return response


# ---------------------------------------------------------------------------
# Telegram send
# ---------------------------------------------------------------------------

def _send_telegram(text: str) -> None:
    """Send a Telegram message to TELEGRAM_OWNER_ID."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    owner_id  = os.getenv("TELEGRAM_OWNER_ID", "").strip()

    if not bot_token or not owner_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_OWNER_ID must be set")

    try:
        send_message(bot_token, owner_id, text)
        log.info("[pi] Telegram message sent OK")
    except requests.RequestException as exc:
        log.error("[pi] Telegram send failed: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def _is_empty_response(text: str) -> bool:
    """Return True if Claude signalled there is nothing actionable."""
    if not text:
        return True
    lower = text.lower().strip()
    empty_signals = ("null", "none", "nothing", "no urgent", "no actionable", "keine")
    # Short responses that are just a null signal
    if len(lower) < 60 and any(lower.startswith(s) for s in empty_signals):
        return True
    return False


def run_proactive_intelligence() -> None:
    today_str = today()
    log.info("[pi] Starting proactive intelligence for %s", today_str)

    context = _build_context(today_str)
    log.info("[pi] Context assembled (%d chars)", len(context))

    try:
        insight = _ask_claude(today_str, context)
    except Exception as exc:
        log.error("[pi] Claude call failed: %s", exc)
        return

    if _is_empty_response(insight):
        log.info("[pi] No actionable insights today — exiting silently")
        return

    log.info("[pi] Actionable insight found — sending Telegram")
    try:
        _send_telegram(insight)
    except Exception as exc:
        log.error("[pi] Failed to deliver insight: %s", exc)


if __name__ == "__main__":
    run_proactive_intelligence()
