"""
Telegram capture bot for julio-brain.

Commands:
  /task <text>   → "- [ ] text" under ## Tasks in today's daily note
  /frage <text>  → "- [ ] text (YYYY-MM-DD)" in 40_Knowledge/open-questions.md
  /note <text>   → text under ## Notes in today's daily note
  <plain text>   → treated as /note
  <voice>        → transcribed via Whisper, treated as /note
  <photo>        → analyzed via GPT-4o Vision, auto-categorized

Daily job at 20:30 Europe/Berlin: open tasks + open questions summary.

Only accepts messages from TELEGRAM_CHAT_ID.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
from datetime import time
from zoneinfo import ZoneInfo

import openai
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from scripts.sync_to_brain import github_read, github_read_modify_write
from scripts.utils import today

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
_OWNER_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

_VISION_PROMPT = (
    "Analyze this image. Reply ONLY with valid JSON on a single line — no markdown, no extra text.\n"
    'Format: {"type": "task" | "note" | "question", "text": "<content>"}\n'
    "Rules:\n"
    "- task: something to do, an action item, a to-do\n"
    "- question: something to look up, research, or decide\n"
    "- note: everything else (screenshot, information, idea, reference)\n"
    "Extract the most relevant content from the image as the text value."
)

_BERLIN = ZoneInfo("Europe/Berlin")

# Lazy-initialized OpenAI client — only accessed when a voice/photo message arrives.
_oai: openai.OpenAI | None = None


def _get_openai() -> openai.OpenAI:
    global _oai
    if _oai is None:
        _oai = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _oai


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

    end = len(lines)
    for i in range(idx + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    insert_pos = end
    while insert_pos > idx + 1 and not lines[insert_pos - 1].strip():
        insert_pos -= 1

    lines.insert(insert_pos, entry)
    return "\n".join(lines) + "\n"


def _daily_mutator(section: str, entry: str):
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
# Vision response parsing
# ---------------------------------------------------------------------------

def _parse_vision_response(text: str) -> tuple[str, str]:
    """Parse GPT-4o JSON response. Returns (type, content). Falls back to ('note', raw)."""
    text = text.strip()
    # Strip ```json ... ``` wrapper if present
    wrapped = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if wrapped:
        text = wrapped.group(1)
    try:
        data = json.loads(text)
        type_ = str(data.get("type", "note")).lower()
        content = str(data.get("text", "")).strip()
        if type_ not in ("task", "note", "question"):
            type_ = "note"
        return type_, content or text
    except (json.JSONDecodeError, KeyError, TypeError):
        return "note", text


# ---------------------------------------------------------------------------
# Evening summary helpers
# ---------------------------------------------------------------------------

def _extract_open_items(text: str, section: str) -> list[str]:
    """Return unchecked '- [ ]' lines from a named ## section only."""
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
    return [l.strip() for l in lines[start:end] if l.strip().startswith("- [ ]")]


def _format_summary(tasks: list[str], questions: list[str], run_date: str) -> str:
    if not tasks and not questions:
        return f"✅ *Abend-Zusammenfassung — {run_date}*\n\nAlles erledigt\\. Guten Abend\\!"

    def bullet(line: str) -> str:
        return "• " + (line[6:] if line.startswith("- [ ] ") else line)

    parts = [f"📋 *Abend\\-Zusammenfassung — {run_date}*"]
    parts.append("\n*Offene Tasks:*" if tasks else "\n*Offene Tasks:* —")
    parts.extend(bullet(t) for t in tasks)
    parts.append("\n*Offene Fragen:*" if questions else "\n*Offene Fragen:* —")
    parts.extend(bullet(q) for q in questions)
    parts.append(f"\n_\\({len(tasks)} Tasks · {len(questions)} Fragen\\)_")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _authorized(update: Update) -> bool:
    return update.effective_chat.id == _OWNER_ID


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

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
# Voice handler
# ---------------------------------------------------------------------------

async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text("🎙 Transkribiere...")
    try:
        tg_file = await update.message.voice.get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        buf.seek(0)

        transcript = _get_openai().audio.transcriptions.create(
            model="whisper-1",
            file=("audio.ogg", buf, "audio/ogg"),
        )
        text = transcript.text.strip()
        if not text:
            await update.message.reply_text("Keine Sprache erkannt.")
            return

        path, mutate = _daily_mutator("Notes", text)
        github_read_modify_write(path, mutate, f"capture: voice note ({today()})")
        await update.message.reply_text(f'🎙 Erkannt: "{text}"\n✓ Note gespeichert.')
    except Exception as e:
        log.error("handle_voice failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


# ---------------------------------------------------------------------------
# Photo handler
# ---------------------------------------------------------------------------

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text("📷 Analysiere...")
    try:
        tg_file = await update.message.photo[-1].get_file()
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        prompt = _VISION_PROMPT
        if update.message.caption:
            prompt += f"\n\nUser caption: {update.message.caption}"

        response = _get_openai().chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=200,
        )
        raw = response.choices[0].message.content or ""
        type_, content = _parse_vision_response(raw)

        label_map = {"task": "Task", "note": "Note", "question": "Frage"}
        label = label_map.get(type_, "Note")

        if type_ == "task":
            path, mutate = _daily_mutator("Tasks", f"- [ ] {content}")
            github_read_modify_write(path, mutate, f"capture: photo task ({today()})")
        elif type_ == "question":
            path, mutate = _questions_mutator(f"- [ ] {content} ({today()})")
            github_read_modify_write(path, mutate, f"capture: photo question ({today()})")
        else:
            path, mutate = _daily_mutator("Notes", content)
            github_read_modify_write(path, mutate, f"capture: photo note ({today()})")

        await update.message.reply_text(f"📷 {label} erkannt: {content}\n✓ Gespeichert.")
    except Exception as e:
        log.error("handle_photo failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


# ---------------------------------------------------------------------------
# Evening summary job
# ---------------------------------------------------------------------------

async def send_evening_summary(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    run_date = today()
    try:
        daily_text  = github_read(f"10_Daily/{run_date}.md") or ""
        tasks       = _extract_open_items(daily_text, "Tasks")
        q_text      = github_read("40_Knowledge/open-questions.md") or ""
        questions   = [l.strip() for l in q_text.splitlines() if l.strip().startswith("- [ ]")]
        msg = _format_summary(tasks, questions, run_date)
        await ctx.bot.send_message(chat_id=_OWNER_ID, text=msg, parse_mode="MarkdownV2")
    except Exception as e:
        log.error("send_evening_summary failed: %s", e)
        try:
            await ctx.bot.send_message(chat_id=_OWNER_ID, text=f"Zusammenfassung fehlgeschlagen: {e}")
        except Exception:
            pass


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
    app.add_handler(MessageHandler(filters.VOICE,                     handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO,                     handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,   plain_text))

    app.job_queue.run_daily(
        send_evening_summary,
        time=time(20, 30, tzinfo=_BERLIN),
    )

    log.info("Telegram bot starting — polling.")
    app.run_polling()


if __name__ == "__main__":
    main()
