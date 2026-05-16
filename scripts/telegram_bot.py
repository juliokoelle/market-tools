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
import time as _time_mod
from datetime import datetime, time
from zoneinfo import ZoneInfo

import openai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from scripts.sync_to_brain import github_read, github_read_modify_write
from scripts.utils import today
from scripts.vault_utils import insert_into_section, make_daily_note as _make_daily_note, note_entry as _note_entry
from scripts.classifier import classify_text, CapturedItem, VALID_TYPES
from scripts.capture_router import route_item

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
_OWNER_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

_VISION_PROMPT = (
    "Analyze this image. Reply ONLY with valid JSON on a single line — no markdown, no extra text.\n"
    'Format: {"type": "task" | "note" | "question" | "shopping_list", "text": "<content>"}\n'
    "Rules:\n"
    "- task: something to do, an action item, a to-do\n"
    "- question: something to look up, research, or decide\n"
    "- shopping_list: a list of items to buy or purchase\n"
    "- note: everything else (screenshot, information, idea, reference)\n"
    "For task and shopping_list, if multiple items exist return them comma-separated in text.\n"
    "Extract the most relevant content from the image as the text value."
)

_BERLIN = ZoneInfo("Europe/Berlin")

_TYPE_EMOJI: dict[str, str] = {
    "wishlist": "🛍️", "stock_pick": "📈", "gift_idea": "🎁",
    "reminder": "⏰", "task": "📋", "question": "❓",
    "idea": "💡", "note": "📝",
}
_TYPE_LABEL: dict[str, str] = {
    "wishlist": "Wishlist", "stock_pick": "Stock Pick", "gift_idea": "Geschenkidee",
    "reminder": "Reminder", "task": "Task", "question": "Frage",
    "idea": "Idee", "note": "Note",
}


def _confirmation_keyboard(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Speichern", callback_data=f"save:{key}"),
        InlineKeyboardButton("✏️ Typ ändern", callback_data=f"retype:{key}"),
        InlineKeyboardButton("❌ Verwerfen", callback_data=f"discard:{key}"),
    ]])


def _type_picker_keyboard(key: str) -> InlineKeyboardMarkup:
    types = [
        ("📋 Task", "task"), ("❓ Frage", "question"),
        ("🛍️ Wishlist", "wishlist"), ("📈 Stock", "stock_pick"),
        ("🎁 Geschenk", "gift_idea"), ("⏰ Reminder", "reminder"),
        ("💡 Idee", "idea"), ("📝 Note", "note"),
    ]
    rows = [
        [InlineKeyboardButton(label, callback_data=f"settype:{t}:{key}") for label, t in types[i:i+4]]
        for i in range(0, len(types), 4)
    ]
    return InlineKeyboardMarkup(rows)


async def _send_confirmations(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE, items: list[CapturedItem]
) -> None:
    """Send one confirmation message per item and store each in pending state."""
    pending: dict = ctx.application.bot_data.setdefault("pending", {})
    for item in items:
        key = str(_time_mod.monotonic_ns())
        pending[key] = {"item": item, "ts": _time_mod.time()}
        emoji = _TYPE_EMOJI.get(item.type, "📝")
        label = _TYPE_LABEL.get(item.type, "Note")
        text = f"{emoji} *{label} erkannt*\n{item.text}"
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=_confirmation_keyboard(key),
        )


async def handle_confirmation(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ✅/✏️/❌ and type-picker button taps."""
    query = update.callback_query
    await query.answer()
    data: str = query.data or ""
    pending: dict = ctx.application.bot_data.get("pending", {})

    if data.startswith("save:"):
        key = data[5:]
        entry = pending.pop(key, None)
        if entry is None:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        item: CapturedItem = entry["item"]
        label = _TYPE_LABEL.get(item.type, "Note")
        await query.edit_message_text(f"✅ Gespeichert als {label}: {item.text}")
        follow_up = await route_item(item)
        if follow_up:
            await query.message.reply_text(follow_up)

    elif data.startswith("discard:"):
        key = data[8:]
        pending.pop(key, None)
        await query.edit_message_text("❌ Verworfen")

    elif data.startswith("retype:"):
        key = data[7:]
        if key not in pending:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        item = pending[key]["item"]
        emoji = _TYPE_EMOJI.get(item.type, "📝")
        label = _TYPE_LABEL.get(item.type, "Note")
        await query.edit_message_text(
            f"{emoji} *{label} erkannt*\n{item.text}\n\nWelcher Typ?",
            parse_mode="Markdown",
            reply_markup=_type_picker_keyboard(key),
        )

    elif data.startswith("settype:"):
        parts = data.split(":", 2)
        if len(parts) != 3:
            return
        _, new_type, key = parts
        if new_type not in VALID_TYPES:
            return
        if key not in pending:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        pending[key]["item"].type = new_type
        item = pending[key]["item"]
        emoji = _TYPE_EMOJI.get(new_type, "📝")
        label = _TYPE_LABEL.get(new_type, "Note")
        await query.edit_message_text(
            f"{emoji} *{label} erkannt*\n{item.text}",
            parse_mode="Markdown",
            reply_markup=_confirmation_keyboard(key),
        )


# Lazy-initialized OpenAI client — only accessed when a voice/photo message arrives.
_oai: openai.OpenAI | None = None


def _get_openai() -> openai.OpenAI:
    global _oai
    if _oai is None:
        _oai = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _oai


# ---------------------------------------------------------------------------
# File mutation helpers (imported from vault_utils)
# ---------------------------------------------------------------------------


def _daily_mutator(section: str, entry: str):
    run_date = today()

    def mutate(current: str) -> str:
        if not current:
            current = _make_daily_note(run_date)
        return insert_into_section(current, section, entry)

    return f"10_Daily/{run_date}.md", mutate


def _daily_mutator_entries(section: str, entries: list[str]):
    """Insert multiple entries into a section in a single GitHub write."""
    run_date = today()

    def mutate(current: str) -> str:
        if not current:
            current = _make_daily_note(run_date)
        result = current
        for entry in entries:
            result = insert_into_section(result, section, entry)
        return result

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
        if type_ not in ("task", "note", "question", "shopping_list"):
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


def _esc(text: str) -> str:
    """Escape a plain-text string for Telegram MarkdownV2."""
    for ch in r'\_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, f'\\{ch}')
    return text


def _format_summary(tasks: list[str], questions: list[str], run_date: str) -> str:
    safe_date = _esc(run_date)
    if not tasks and not questions:
        return f"✅ *Abend\\-Zusammenfassung — {safe_date}*\n\nAlles erledigt\\. Guten Abend\\!"

    def bullet(line: str) -> str:
        content = line[6:] if line.startswith("- [ ] ") else line
        return "• " + _esc(content)

    parts = [f"📋 *Abend\\-Zusammenfassung — {safe_date}*"]
    parts.append("\n*Offene Tasks:*" if tasks else "\n*Offene Tasks:* —")
    parts.extend(bullet(t) for t in tasks)
    parts.append("\n*Offene Fragen:*" if questions else "\n*Offene Fragen:* —")
    parts.extend(bullet(q) for q in questions)
    parts.append(f"\n_{len(tasks)} Tasks · {len(questions)} Fragen_")
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
    path, mutate = _daily_mutator("Notes", _note_entry(text))
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
    await update.message.reply_text("🔍 Erkenne…")
    items = classify_text(text)
    await _send_confirmations(update, ctx, items)


# ---------------------------------------------------------------------------
# Voice handler
# ---------------------------------------------------------------------------

async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text("🎙 Transkribiere…")
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
        await update.message.reply_text(f'🎙 Erkannt: "{text}"\n🔍 Klassifiziere…')
        items = classify_text(text)
        await _send_confirmations(update, ctx, items)
    except Exception as e:
        log.error("handle_voice failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


# ---------------------------------------------------------------------------
# Photo handler
# ---------------------------------------------------------------------------

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    await update.message.reply_text("📷 Analysiere…")
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

        if type_ == "shopping_list":
            raw_items = [i.strip() for i in content.split(",") if i.strip()]
            items = [
                CapturedItem(type="wishlist", text=i, metadata={"name": i})
                for i in raw_items
            ]
        else:
            type_map = {"task": "task", "note": "note", "question": "question"}
            mapped = type_map.get(type_, "note")
            items = [CapturedItem(type=mapped, text=content, metadata={})]

        await _send_confirmations(update, ctx, items)
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


async def flush_pending(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Flush unconfirmed items older than 24 h as notes. Runs daily at 23:55."""
    pending: dict = ctx.application.bot_data.get("pending", {})
    cutoff = _time_mod.time() - 86400
    to_flush = [k for k, v in list(pending.items()) if v.get("ts", 0) < cutoff]
    for key in to_flush:
        entry = pending.pop(key, None)
        if entry:
            item: CapturedItem = entry["item"]
            item.type = "note"
            try:
                await route_item(item)
            except Exception as e:
                log.error("flush_pending: failed to save item %r: %s", item.text, e)
    if to_flush:
        log.info("flush_pending: flushed %d expired items as notes", len(to_flush))
        try:
            await ctx.bot.send_message(
                chat_id=_OWNER_ID,
                text=f"🗑 {len(to_flush)} unbestätigte Item(s) automatisch als Note gespeichert.",
            )
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
    app.add_handler(CallbackQueryHandler(handle_confirmation))

    app.job_queue.run_daily(
        send_evening_summary,
        time=time(20, 30, tzinfo=_BERLIN),
    )
    app.job_queue.run_daily(
        flush_pending,
        time=time(23, 55, tzinfo=_BERLIN),
    )

    log.info("Telegram bot starting — polling.")
    app.run_polling()


if __name__ == "__main__":
    main()
