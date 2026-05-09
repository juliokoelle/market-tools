"""
Telegram capture bot for julio-brain.

Commands:
  /task <text>   → "- [ ] text" under ## Tasks in today's daily note
  /frage <text>  → "- [ ] text (YYYY-MM-DD)" in 40_Knowledge/open-questions.md
  /note <text>   → text under ## Notes in today's daily note
  <plain text>   → treated as /note

Only accepts messages from TELEGRAM_CHAT_ID.
"""

from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from scripts.sync_to_brain import github_read_modify_write
from scripts.utils import today

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
_OWNER_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))


# ---------------------------------------------------------------------------
# File mutation helpers
# ---------------------------------------------------------------------------

def _make_daily_note(run_date: str) -> str:
    return (
        f"---\ndate: {run_date}\ntype: daily\n---\n\n"
        f"# {run_date}\n\n"
        "## Tasks\n\n"
        "## Notes\n\n"
        "## Focus\n\n"
        "## Log\n\n"
        "## Open Questions\n\n"
        "## People\n\n"
        "## Follow-ups\n\n"
        "---\n\n"
        "*Briefing auto-synced from market-tools at ~08:15 CEST.*\n"
    )


def insert_into_section(text: str, section: str, entry: str) -> str:
    """Append entry as last line of ## section content (before the next ## heading)."""
    lines = text.splitlines()
    header = f"## {section}"

    try:
        idx = next(i for i, l in enumerate(lines) if l.rstrip() == header)
    except StopIteration:
        return text.rstrip("\n") + f"\n\n## {section}\n\n{entry}\n"

    # find end of section (next ## heading or EOF)
    end = len(lines)
    for i in range(idx + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    # insert before any trailing blank lines at the section boundary
    insert_pos = end
    while insert_pos > idx + 1 and not lines[insert_pos - 1].strip():
        insert_pos -= 1

    lines.insert(insert_pos, entry)
    return "\n".join(lines) + "\n"


def _daily_mutator(section: str, entry: str):
    """Returns (path, mutate_fn) for today's daily note."""
    run_date = today()

    def mutate(current: str) -> str:
        if not current:
            current = _make_daily_note(run_date)
        return insert_into_section(current, section, entry)

    return f"10_Daily/{run_date}.md", mutate


def _questions_mutator(entry: str):
    def mutate(current: str) -> str:
        if not current:
            current = "# Open Questions\n\n"
        return current.rstrip("\n") + "\n" + entry + "\n"

    return "40_Knowledge/open-questions.md", mutate


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _authorized(update: Update) -> bool:
    return update.effective_chat.id == _OWNER_ID


async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    text = " ".join(ctx.args).strip()
    if not text:
        await update.message.reply_text("Usage: /task <text>")
        return
    path, mutate = _daily_mutator("Tasks", f"- [ ] {text}")
    try:
        github_read_modify_write(path, mutate, f"capture: task ({today()})")
        await update.message.reply_text("✓ Task gespeichert.")
    except Exception as e:
        log.error("cmd_task failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


async def cmd_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    text = " ".join(ctx.args).strip()
    if not text:
        await update.message.reply_text("Usage: /note <text>")
        return
    path, mutate = _daily_mutator("Notes", text)
    try:
        github_read_modify_write(path, mutate, f"capture: note ({today()})")
        await update.message.reply_text("✓ Note gespeichert.")
    except Exception as e:
        log.error("cmd_note failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


async def cmd_frage(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    text = " ".join(ctx.args).strip()
    if not text:
        await update.message.reply_text("Usage: /frage <text>")
        return
    path, mutate = _questions_mutator(f"- [ ] {text} ({today()})")
    try:
        github_read_modify_write(path, mutate, f"capture: question ({today()})")
        await update.message.reply_text("✓ Frage gespeichert.")
    except Exception as e:
        log.error("cmd_frage failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


async def plain_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    text = (update.message.text or "").strip()
    if not text:
        return
    path, mutate = _daily_mutator("Notes", text)
    try:
        github_read_modify_write(path, mutate, f"capture: note ({today()})")
        await update.message.reply_text("✓ Note gespeichert.")
    except Exception as e:
        log.error("plain_text failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not _TOKEN or not _OWNER_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
    app = Application.builder().token(_TOKEN).build()
    app.add_handler(CommandHandler("task",  cmd_task))
    app.add_handler(CommandHandler("note",  cmd_note))
    app.add_handler(CommandHandler("frage", cmd_frage))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text))
    log.info("Telegram bot starting — polling.")
    app.run_polling()


if __name__ == "__main__":
    main()
