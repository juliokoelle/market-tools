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
Daily job at 21:00 Europe/Berlin: evening recap prompt.

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
from datetime import datetime, time, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from zoneinfo import ZoneInfo

import openai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
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
from scripts.redis_state import (
    get_redis,
    heartbeat,
    install_redis_log_handler,
    last_heartbeat,
    read_recent_logs,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Identifies this process in the shared Redis log sink / heartbeat (see /health).
_SERVICE = "telegram-bot"

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
    "reminder": "⏰", "task": "📋", "task_done": "✅", "question": "❓",
    "idea": "💡", "note": "📝",
}
_TYPE_LABEL: dict[str, str] = {
    "wishlist": "Wishlist", "stock_pick": "Stock Pick", "gift_idea": "Geschenkidee",
    "reminder": "Reminder", "task": "Task", "task_done": "Erledigt",
    "question": "Frage", "idea": "Idee", "note": "Note",
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


# ---------------------------------------------------------------------------
# Pending-state store (Redis-backed, survives redeploys; in-memory fallback)
#
# Confirmation cards reference a pending item by key. Storing this only in
# bot_data meant every Coolify redeploy silently orphaned in-flight cards.
# We now persist in the shared Redis; if Redis is unavailable we transparently
# fall back to ctx.application.bot_data so nothing breaks locally.
# ---------------------------------------------------------------------------

_PENDING_HKEY = "tg:pending"
_RECAP_KEY = "tg:recap_msg_id"
_PENDING_TTL = 2 * 86400  # safety expiry; flush_pending handles the logical 24h


def _ser_item(item: CapturedItem) -> dict:
    return {"type": item.type, "text": item.text, "metadata": item.metadata}


def _deser_item(d: dict) -> CapturedItem:
    return CapturedItem(
        type=d.get("type", "note"),
        text=d.get("text", ""),
        metadata=d.get("metadata") or {},
    )


def _pending_put(bot_data: dict, key: str, item: CapturedItem) -> None:
    ts = _time_mod.time()
    r = get_redis()
    if r is not None:
        try:
            r.hset(_PENDING_HKEY, key, json.dumps({"item": _ser_item(item), "ts": ts}))
            r.expire(_PENDING_HKEY, _PENDING_TTL)
            return
        except Exception as e:  # noqa: BLE001
            log.warning("pending put via Redis failed (%s) — using memory", e)
    bot_data.setdefault("pending", {})[key] = {"item": item, "ts": ts}


def _pending_get(bot_data: dict, key: str) -> tuple[CapturedItem, float] | None:
    r = get_redis()
    if r is not None:
        try:
            raw = r.hget(_PENDING_HKEY, key)
            if raw is None:
                return None
            d = json.loads(raw)
            return _deser_item(d["item"]), d.get("ts", 0.0)
        except Exception as e:  # noqa: BLE001
            log.warning("pending get via Redis failed (%s)", e)
    entry = bot_data.get("pending", {}).get(key)
    return (entry["item"], entry.get("ts", 0.0)) if entry else None


def _pending_pop(bot_data: dict, key: str) -> tuple[CapturedItem, float] | None:
    r = get_redis()
    if r is not None:
        try:
            raw = r.hget(_PENDING_HKEY, key)
            if raw is None:
                return None
            r.hdel(_PENDING_HKEY, key)
            d = json.loads(raw)
            return _deser_item(d["item"]), d.get("ts", 0.0)
        except Exception as e:  # noqa: BLE001
            log.warning("pending pop via Redis failed (%s)", e)
    entry = bot_data.get("pending", {}).pop(key, None)
    return (entry["item"], entry.get("ts", 0.0)) if entry else None


def _pending_remove(bot_data: dict, key: str) -> None:
    r = get_redis()
    if r is not None:
        try:
            r.hdel(_PENDING_HKEY, key)
            return
        except Exception:  # noqa: BLE001
            pass
    bot_data.get("pending", {}).pop(key, None)


def _pending_set_type(bot_data: dict, key: str, new_type: str) -> CapturedItem | None:
    r = get_redis()
    if r is not None:
        try:
            raw = r.hget(_PENDING_HKEY, key)
            if raw is None:
                return None
            d = json.loads(raw)
            d["item"]["type"] = new_type
            r.hset(_PENDING_HKEY, key, json.dumps(d))
            return _deser_item(d["item"])
        except Exception as e:  # noqa: BLE001
            log.warning("pending set_type via Redis failed (%s)", e)
    entry = bot_data.get("pending", {}).get(key)
    if entry is None:
        return None
    entry["item"].type = new_type
    return entry["item"]


def _pending_all(bot_data: dict) -> dict[str, tuple[CapturedItem, float]]:
    r = get_redis()
    if r is not None:
        try:
            out: dict[str, tuple[CapturedItem, float]] = {}
            for k, raw in (r.hgetall(_PENDING_HKEY) or {}).items():
                d = json.loads(raw)
                out[k] = (_deser_item(d["item"]), d.get("ts", 0.0))
            return out
        except Exception as e:  # noqa: BLE001
            log.warning("pending all via Redis failed (%s)", e)
    return {k: (v["item"], v.get("ts", 0.0)) for k, v in bot_data.get("pending", {}).items()}


def _recap_set(bot_data: dict, msg_id: int) -> None:
    r = get_redis()
    if r is not None:
        try:
            r.set(_RECAP_KEY, msg_id, ex=_PENDING_TTL)
            return
        except Exception:  # noqa: BLE001
            pass
    bot_data["recap_msg_id"] = msg_id


def _recap_get(bot_data: dict) -> int | None:
    r = get_redis()
    if r is not None:
        try:
            v = r.get(_RECAP_KEY)
            return int(v) if v is not None else None
        except Exception:  # noqa: BLE001
            pass
    return bot_data.get("recap_msg_id")


def _card_text(emoji: str, label: str, text: str, suffix: str | None = None) -> str:
    """Build a MarkdownV2 confirmation card with all dynamic text safely escaped.

    Card text previously used legacy Markdown with raw item text, so any '_', '*',
    '[' or backtick (common in transcripts, tickers, URLs) made Telegram reject
    the message and the card never appeared.
    """
    out = f"{emoji} *{label} erkannt*\n{_esc(text)}"
    if suffix:
        out += f"\n\n{_esc(suffix)}"
    return out


async def _safe_reply(message, text: str, parse_mode: str = ParseMode.MARKDOWN) -> None:
    """Reply with Markdown, falling back to plain text if entity parsing fails.

    Follow-up messages (stock snapshots, question answers) carry LLM/free text
    that can contain unbalanced Markdown; this guarantees the message arrives.
    """
    try:
        await message.reply_text(text, parse_mode=parse_mode)
    except BadRequest as e:
        log.warning("Markdown reply failed (%s) — sending plain", e)
        await message.reply_text(text)


async def _send_confirmations(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE, items: list[CapturedItem]
) -> None:
    """Send one confirmation message per item and store each in pending state."""
    bot_data = ctx.application.bot_data
    for item in items:
        key = str(_time_mod.monotonic_ns())
        _pending_put(bot_data, key, item)
        emoji = _TYPE_EMOJI.get(item.type, "📝")
        label = _TYPE_LABEL.get(item.type, "Note")
        await update.message.reply_text(
            _card_text(emoji, label, item.text),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_confirmation_keyboard(key),
        )


async def handle_confirmation(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ✅/✏️/❌ and type-picker button taps."""
    query = update.callback_query
    await query.answer()
    data: str = query.data or ""
    bot_data = ctx.application.bot_data

    if data.startswith("save:"):
        key = data[5:]
        got = _pending_pop(bot_data, key)
        if got is None:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        item, _ = got
        label = _TYPE_LABEL.get(item.type, "Note")
        await query.edit_message_text(f"✅ Gespeichert als {label}: {item.text}")
        follow_up = await route_item(item)
        if follow_up:
            await _safe_reply(query.message, follow_up)

    elif data.startswith("discard:"):
        key = data[8:]
        _pending_remove(bot_data, key)
        await query.edit_message_text("❌ Verworfen")

    elif data.startswith("retype:"):
        key = data[7:]
        got = _pending_get(bot_data, key)
        if got is None:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        item, _ = got
        emoji = _TYPE_EMOJI.get(item.type, "📝")
        label = _TYPE_LABEL.get(item.type, "Note")
        await query.edit_message_text(
            _card_text(emoji, label, item.text, "Welcher Typ?"),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_type_picker_keyboard(key),
        )

    elif data.startswith("settype:"):
        parts = data.split(":", 2)
        if len(parts) != 3:
            return
        _, new_type, key = parts
        if new_type not in VALID_TYPES:
            return
        item = _pending_set_type(bot_data, key, new_type)
        if item is None:
            await query.edit_message_reply_markup(reply_markup=None)
            return
        emoji = _TYPE_EMOJI.get(new_type, "📝")
        label = _TYPE_LABEL.get(new_type, "Note")
        await query.edit_message_text(
            _card_text(emoji, label, item.text),
            parse_mode=ParseMode.MARKDOWN_V2,
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


async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Return current open tasks on demand via /tasks."""
    if not _authorized(update):
        return
    run_date = today()
    try:
        daily_text  = github_read(f"10_Daily/{run_date}.md") or ""
        daily_tasks = _extract_open_items(daily_text, "Tasks")
        vault_tasks = _get_vault_tasks()
        tasks       = daily_tasks + vault_tasks
        q_text      = github_read("40_Knowledge/open-questions.md") or ""
        questions   = [l.strip() for l in q_text.splitlines() if l.strip().startswith("- [ ]")]
        msg = _format_summary(tasks, questions, run_date)
        await update.message.reply_text(msg, parse_mode="MarkdownV2")
    except Exception as e:
        log.error("cmd_tasks failed: %s", e)
        await update.message.reply_text(f"Fehler: {e}")


def _read_log_file(service: str, hours: int) -> tuple[list[str], list[str]]:
    """Fallback log source: parse logs/<service>.log when Redis has nothing.

    Only sees files in this container's filesystem (i.e. telegram-bot's own log).
    """
    path = Path(__file__).parent.parent / "logs" / f"{service}.log"
    errors: list[str] = []
    warnings: list[str] = []
    if not path.exists():
        return errors, warnings
    cutoff = datetime.now() - timedelta(hours=hours)
    for line in path.read_text(errors="replace").splitlines():
        # Lines look like: 2026-05-31 08:15:42 ERROR scripts.foo: message
        try:
            ts = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if ts < cutoff:
            continue
        upper = line.upper()
        if " ERROR " in upper:
            errors.append(line[upper.find(" ERROR ") + 7:][:160])
        elif " WARNING " in upper:
            warnings.append(line[upper.find(" WARNING ") + 9:][:160])
    return errors, warnings


async def cmd_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not _authorized(update):
        return
    # Pulled from the shared Redis log sink so we see other containers too.
    services = {
        "telegram-bot": "Telegram Bot",
        "gmail-briefing": "Gmail Briefing",
        "cache-warmer": "Cache Warmer",
    }
    parts: list[str] = ["🩺 *System Health — letzte 24h*\n"]
    total_errors = 0
    for svc, label in services.items():
        errors, warnings = read_recent_logs(svc, 24)
        if not errors and not warnings:  # Redis empty → try local file
            ferr, fwarn = _read_log_file(svc, 24)
            errors, warnings = ferr, fwarn
        hb = last_heartbeat(svc)

        if errors:
            status = "🔴"
        elif hb is not None:
            status = "✅"
        else:
            status = "⚪"  # no errors AND no liveness signal — unknown, not "OK"

        live = ""
        if hb is not None:
            mins = int((_time_mod.time() - hb) / 60)
            live = " · aktiv" if mins <= 0 else f" · aktiv vor {mins}m"
        parts.append(f"{status} *{label}*{live}")

        if errors:
            total_errors += len(errors)
            for e in errors[-3:]:
                parts.append(f"  ❌ {e}")
            if len(errors) > 3:
                parts.append(f"  … +{len(errors) - 3} weitere")
        if warnings:
            for w in warnings[-2:]:
                parts.append(f"  ⚠️ {w}")
        if not errors and not warnings:
            parts.append("  Keine Fehler" if hb is not None else "  Keine Daten")
        parts.append("")

    parts.append(
        "_Keine Fehler in den letzten 24h_ ✅" if total_errors == 0
        else f"_⚠️ {total_errors} Fehler gefunden_"
    )
    await _safe_reply(update.message, "\n".join(parts), parse_mode=ParseMode.MARKDOWN)


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

    # Feature 2: Check if this is a reply to the evening recap prompt
    if (
        update.message.reply_to_message is not None
        and update.message.reply_to_message.message_id
            == _recap_get(ctx.application.bot_data)
    ):
        run_date = today()
        entry = _note_entry(text)
        path = f"10_Daily/{run_date}.md"

        def mutate(current: str) -> str:
            if not current:
                current = _make_daily_note(run_date)
            return insert_into_section(current, "Log", entry)

        try:
            github_read_modify_write(path, mutate, f"capture: recap ({run_date})")
            await update.message.reply_text("✅ Tages-Recap gespeichert.")
        except Exception as e:
            log.error("recap save failed: %s", e)
            await update.message.reply_text(f"Fehler: {e}")
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

        # Feature 2: Check if this voice message is a reply to the evening recap prompt
        if (
            update.message.reply_to_message is not None
            and update.message.reply_to_message.message_id
                == ctx.application.bot_data.get("recap_msg_id")
        ):
            run_date = today()
            entry = _note_entry(text)
            path = f"10_Daily/{run_date}.md"

            def mutate(current: str) -> str:
                if not current:
                    current = _make_daily_note(run_date)
                return insert_into_section(current, "Log", entry)

            try:
                github_read_modify_write(path, mutate, f"capture: recap ({run_date})")
                await update.message.reply_text("✅ Tages-Recap gespeichert.")
            except Exception as e:
                log.error("recap (voice) save failed: %s", e)
                await update.message.reply_text(f"Fehler: {e}")
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


def _get_vault_tasks() -> list[str]:
    """Read all open tasks from 00_Inbox/OPEN_TASKS.md."""
    text = github_read("00_Inbox/OPEN_TASKS.md") or ""
    return [l.strip() for l in text.splitlines() if l.strip().startswith("- [ ]")]


async def send_evening_summary(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    run_date = today()
    try:
        daily_text  = github_read(f"10_Daily/{run_date}.md") or ""
        daily_tasks = _extract_open_items(daily_text, "Tasks")
        vault_tasks = _get_vault_tasks()
        tasks       = daily_tasks + vault_tasks
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
# Evening recap job (Feature 1)
# ---------------------------------------------------------------------------

async def send_evening_recap_prompt(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the daily recap prompt at 21:00 and store the message ID for reply detection."""
    try:
        sent = await ctx.bot.send_message(
            chat_id=_OWNER_ID,
            text="📔 *Tages-Recap* — Wie war dein Tag? Antworte auf diese Nachricht mit deiner Zusammenfassung.",
            parse_mode=ParseMode.MARKDOWN,
        )
        _recap_set(ctx.application.bot_data, sent.message_id)
    except Exception as e:
        log.error("send_evening_recap_prompt failed: %s", e)


async def flush_pending(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Flush unconfirmed items older than 24 h as notes. Runs daily at 23:55."""
    bot_data = ctx.application.bot_data
    cutoff = _time_mod.time() - 86400
    expired = [(k, item) for k, (item, ts) in _pending_all(bot_data).items() if ts < cutoff]
    to_flush: list[str] = []
    for key, item in expired:
        item.type = "note"
        try:
            await route_item(item)
            _pending_remove(bot_data, key)  # only drop after a successful save
            to_flush.append(key)
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

async def _heartbeat_job(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Record liveness so /health can tell 'silent-healthy' from 'dead'."""
    heartbeat(_SERVICE)


def _configure_logging() -> None:
    """Write rotating file logs (so /health's file fallback works) and push
    WARNING+ records to the shared Redis sink (so /health sees other services)."""
    log_dir = Path(__file__).parent.parent / "logs"
    try:
        log_dir.mkdir(exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / f"{_SERVICE}.log", maxBytes=1_000_000, backupCount=2
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logging.getLogger().addHandler(fh)
    except Exception as e:  # noqa: BLE001 — file logging is best-effort
        log.warning("file logging unavailable (%s)", e)
    install_redis_log_handler(_SERVICE)


def main() -> None:
    if not _TOKEN or not _OWNER_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")

    _configure_logging()

    app = Application.builder().token(_TOKEN).build()
    app.add_handler(CommandHandler("task",   cmd_task))
    app.add_handler(CommandHandler("note",   cmd_note))
    app.add_handler(CommandHandler("frage",  cmd_frage))
    app.add_handler(CommandHandler("tasks",  cmd_tasks))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(MessageHandler(filters.VOICE,                     handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO,                     handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,   plain_text))
    app.add_handler(CallbackQueryHandler(handle_confirmation))

    app.job_queue.run_daily(
        send_evening_summary,
        time=time(20, 30, tzinfo=_BERLIN),
    )
    app.job_queue.run_daily(
        send_evening_recap_prompt,
        time=time(21, 0, tzinfo=_BERLIN),
    )
    app.job_queue.run_daily(
        flush_pending,
        time=time(23, 55, tzinfo=_BERLIN),
    )
    # Liveness heartbeat for /health (first beat immediately, then every 5 min).
    app.job_queue.run_repeating(_heartbeat_job, interval=300, first=0)

    log.info("Telegram bot starting — polling.")
    app.run_polling()


if __name__ == "__main__":
    main()
