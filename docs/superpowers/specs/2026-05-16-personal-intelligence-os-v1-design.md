# Personal Intelligence OS v1 — NLP Classifier + Routing Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the Telegram bot to automatically classify all unstructured inputs (text, voice, photo) into typed items, present inline-button confirmation, and route each confirmed item to the correct integration (Obsidian vault, MyWardrobe wishlist API, Market Tools watchlist endpoint).

**Architecture:** Three new modules added to `scripts/`: `classifier.py` (LLM extraction), `capture_router.py` (dispatch per type). `telegram_bot.py` gets confirmation flow with Telegram inline keyboards and pending-item state management. A new FastAPI endpoint `POST /watchlist` is added to `api.py`.

**Tech Stack:** Python, python-telegram-bot v20, Anthropic claude-haiku-4-5, existing GitHub API sync pattern, MyWardrobe Vercel API, FastAPI (market-tools backend).

---

## 1. Classifier (`scripts/classifier.py`)

Single Claude call (claude-haiku-4-5) for every unstructured input. Input is a plain string (pre-transcribed voice, plain text, or photo-extracted text). Output is a JSON array of `CapturedItem` objects.

### CapturedItem schema

```python
@dataclass
class CapturedItem:
    type: str      # see types below
    text: str      # human-readable summary of what was captured
    metadata: dict # type-specific fields
```

### Types and metadata

| type | metadata fields | routing target |
|------|----------------|----------------|
| `wishlist` | `name`, `brand?`, `price?` | Obsidian `## Shopping List` + MyWardrobe API |
| `stock_pick` | `ticker`, `notes?` | Obsidian `## Notes` + Market Tools `/watchlist` |
| `gift_idea` | `person`, `item` | `50_People/{person}.md` → `## Geschenkideen` |
| `reminder` | `text`, `date?` | Obsidian `## Follow-ups` (appears in evening summary) |
| `task` | _(none)_ | Obsidian `## Tasks` (existing flow) |
| `question` | _(none)_ | `40_Knowledge/open-questions.md` (existing flow) |
| `idea` | _(none)_ | Obsidian `## Notes` with 💡 prefix |
| `note` | _(none)_ | Obsidian `## Notes` (existing flow) |

### Classifier prompt rules

The system prompt instructs Claude to return **only valid JSON**, no markdown. Classification rules:

- `wishlist` — speaker wants to buy, own, or get something ("ich will X kaufen", "brauche X", "bestellen")
- `stock_pick` — a company or ticker in an investing context ("ASML ist interessant", "finde X spannend", "schaue mir X an")
- `gift_idea` — item intended for a named person ("für Mama", "Nick würde X gefallen")
- `reminder` — time-anchored note ("erinnere mich", "nicht vergessen", "bis Montag")
- `task` — concrete action to complete ("Mail schreiben", "anrufen", "erledigen")
- `question` — something to look up or decide ("wie funktioniert X", "was ist besser")
- `idea` — concept, project idea, observation without direct action
- `note` — everything else

One message may produce multiple items (e.g. a voice note listing a shopping list + a stock mention → array of 2+). Fallback: if classification fails or returns invalid JSON, the entire input is saved as `note`.

---

## 2. Confirmation Flow (`telegram_bot.py` additions)

### Trigger

Only unstructured inputs go through the classifier:
- Plain text messages (no `/` command prefix)
- Voice messages (after Whisper transcription)
- Photo messages (after GPT-4o Vision extraction)

Existing commands (`/task`, `/note`, `/frage`) bypass classification entirely and save immediately as before.

### Per-item confirmation message

For each `CapturedItem` the bot sends a separate Telegram message:

```
{type_emoji} {type_label} erkannt
{item.text}

[✅ Speichern]  [✏️ Typ ändern]  [❌ Verwerfen]
```

Type emojis: 🛍️ wishlist · 📈 stock_pick · 🎁 gift_idea · ⏰ reminder · 📋 task · ❓ question · 💡 idea · 📝 note

### "Typ ändern" secondary keyboard

```
Welcher Typ?
[📋 Task]     [❓ Frage]   [🛍️ Wishlist]  [📈 Stock]
[🎁 Geschenk] [⏰ Reminder] [💡 Idee]      [📝 Note]
```

After selection: bot edits the message back to the primary confirmation view with the new type.

### State management

Pending items stored in `context.bot_data["pending"][message_id]` as `CapturedItem`. After ✅ or ❌: item is removed from state, message is edited to "✅ Gespeichert als {type_label}" or "❌ Verworfen".

**Timeout fallback:** A daily job at 23:55 Europe/Berlin flushes all items still in `pending` older than 24h as `note` to the Daily Note, then clears them. No input is ever lost.

---

## 3. Router (`scripts/capture_router.py`)

Single public function: `async def route_item(item: CapturedItem) -> None`

Dispatches based on `item.type`. All Obsidian writes use the existing `github_read_modify_write` pattern. External API calls use `httpx.AsyncClient`.

### Per-type routing logic

**wishlist**
1. `github_read_modify_write`: insert `- [ ] {name} ({brand})` into `## Shopping List` of today's Daily Note
2. `POST https://mywardrobe-dun.vercel.app/api/wishlist` with `{name, brand, price, priority: 2, currency: "EUR"}`

**stock_pick**
1. `github_read_modify_write`: insert `- 📈 ${ticker} — {notes}` into `## Notes` of today's Daily Note
2. `POST {MARKET_TOOLS_BACKEND}/watchlist` with `{ticker, notes, added_date}`

**gift_idea**
1. Normalize person name to filename: `unicodedata.normalize("NFC", name).lower()`, spaces → hyphens, `.md` suffix (preserves Umlaute: "Müller" → `müller.md`)
2. `github_read_modify_write` on `50_People/{filename}`: if file empty, create with frontmatter + `## Geschenkideen` section; otherwise append `- {item} ({today()})` to `## Geschenkideen`

**reminder**
1. `github_read_modify_write`: insert `- [ ] {text}` into `## Follow-ups` of today's Daily Note

**task**
1. Existing `_daily_mutator("Tasks", f"- [ ] {item.text}")` — no change

**question**
1. Existing `_questions_mutator(f"- [ ] {item.text} ({today()})")` — no change

**idea**
1. `github_read_modify_write`: insert `- 💡 {item.text}` into `## Notes` of today's Daily Note

**note**
1. `github_read_modify_write`: insert `- [{time}] {item.text}` into `## Notes` of today's Daily Note

---

## 4. Market Tools Watchlist Endpoint (`scripts/api.py`)

New FastAPI endpoint added to the existing market-tools backend.

### Storage

`data/watchlist.json` in the market-tools GitHub repo (same GitHub API pattern as briefings). Structure:

```json
[
  {"ticker": "ASML", "notes": "AI infrastructure play", "added": "2026-05-16"},
  {"ticker": "NVDA", "notes": "already in portfolio, watching for add", "added": "2026-05-14"}
]
```

### Endpoints

```
GET  /watchlist           → returns full watchlist array
POST /watchlist           → body: {ticker, notes?} → appends, returns updated list
DELETE /watchlist/{ticker} → removes entry, returns updated list
```

Reads/writes via `github_read_modify_write` on `data/watchlist.json`. No Supabase needed. Frontend display is out of scope for this spec (Sub-project 3).

---

## 5. File Changes Summary

| File | Change |
|------|--------|
| `scripts/classifier.py` | NEW — LLM classifier, `CapturedItem` dataclass, `classify_text(text) → list[CapturedItem]` |
| `scripts/capture_router.py` | NEW — `route_item(item)`, all per-type dispatch logic |
| `scripts/telegram_bot.py` | MODIFY — plain_text, handle_voice, handle_photo now call classifier → confirmation flow; add `CallbackQueryHandler`; add 23:55 timeout job |
| `scripts/api.py` | MODIFY — add `/watchlist` GET, POST, DELETE endpoints |
| `data/watchlist.json` | NEW — empty array `[]` as initial state |

---

## 6. Out of Scope (Sub-project 3+)

- Market Tools frontend display of watchlist
- AI-powered evening digest that answers open questions
- Claude Code session capture
- Price/image enrichment for wishlist items (manual in MyWardrobe app)
