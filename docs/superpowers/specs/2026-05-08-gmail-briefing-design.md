---
title: Gmail Briefing Ingestion
date: 2026-05-08
status: approved
---

# Gmail Briefing Ingestion — Design Spec

## Goal

Replace the LLM-generated Daily Briefing (Anthropic/OpenAI + NewsAPI + market data fetch) with
direct ingestion of two daily newsletter emails from morningcrunch.de. The website display, Obsidian
sync, and all GET endpoints remain unchanged. Only the content-generation step changes.

---

## Senders

| Newsletter | From address | Content |
|---|---|---|
| MarketsXrunch | `markets@m.morningcrunch.de` | Markets & Finance |
| DealsXrunch | `deals@m2.morningcrunch.de` | Deals & Business |

Both arrive daily at ~05:59 UTC. Both are HTML email bodies (no attachments).
The Render Cron runs at 06:15 UTC (08:15 CEST) — 16-minute buffer after delivery.

---

## Architecture

### Data Flow

```
[Render Cron 06:15 UTC]
    └── scripts/run_gmail_briefing.py        (new entry point)
            └── scripts/fetch_gmail_briefing.py  (core logic)
                    ├── IMAP connect to imap.gmail.com:993
                    ├── Search: FROM markets@m.morningcrunch.de SINCE today
                    ├── Search: FROM deals@m2.morningcrunch.de  SINCE today
                    ├── Extract text/html MIME part from each email
                    ├── html2text → structured Markdown (both emails)
                    └── Combine: Markets section first, Deals section second
            ├── Save: outputs/YYYY-MM-DD-briefing.md
            ├── Save: outputs/latest-briefing.md
            └── sync_to_brain(date, content)         (unchanged)
                    └── GitHub API → julio-brain/10_Daily/YYYY-MM-DD.md
                                        └── Website reads as before
```

### Component Status

| Component | Change | Notes |
|---|---|---|
| `scripts/fetch_gmail_briefing.py` | **NEW** | Core Gmail + conversion logic |
| `scripts/run_gmail_briefing.py` | **NEW** | Cron entry point |
| `render.yaml` | **EXTENDED** | New cron service |
| `requirements.txt` | **EXTENDED** | +html2text |
| `api.py POST /briefing/generate` | **DISABLED** | Returns 410 Gone |
| `api.py POST /generate-briefing` | **DISABLED** | Returns 410 Gone (legacy) |
| `frontend/index.html` | **MODIFIED** | Generate buttons removed |
| `sync_to_brain.py` | **UNCHANGED** | |
| All `GET /briefing/*` endpoints | **UNCHANGED** | Website display unaffected |
| `run_daily.py` | **DEACTIVATED** | Kept, not called |
| `fetch_data.py`, `news_sources.py` | **KEPT** | Not called for briefing |
| `generate_briefing.py` | **KEPT** | Still used by `/stock/{ticker}/ai-summary` |

---

## `fetch_gmail_briefing.py`

### Environment Variables

| Variable | Description |
|---|---|
| `GMAIL_USERNAME` | Full Gmail address, e.g. `juliokoelle@gmail.com` |
| `GMAIL_APP_PASSWORD` | 16-char Google App Password (no spaces) |

### IMAP Search Logic

1. TLS connect to `imap.gmail.com:993`
2. Login with `GMAIL_USERNAME` + `GMAIL_APP_PASSWORD`
3. `SELECT "INBOX"` — fallback to `[Gmail]/All Mail` if search returns 0 results
4. Per sender: `SEARCH (FROM "{sender}" SINCE {DD-Mon-YYYY})`
5. If multiple results: take the most recent message (highest UID)
6. Fetch full RFC 2822 message, traverse MIME tree for `text/html` part

### HTML → Markdown Conversion

Library: `html2text`

```python
h = html2text.HTML2Text()
h.ignore_links  = False   # preserve hyperlinks
h.ignore_images = True    # skip tracking pixels and inline images
h.body_width    = 0       # no automatic line wrapping
h.unicode_snob  = True    # preserve ä ö ü ß correctly
```

Post-processing pipeline (in order):
1. Collapse 3+ consecutive blank lines → 2
2. Strip known footer patterns: lines matching `Abmelde`, `Unsubscribe`, `©`, `Impressum`, `mailto:` standalone lines
3. Strip leading/trailing whitespace from the full document

### Combined Output Format

```markdown
## MarketsXrunch — Markets & Finance

{converted content from markets@m.morningcrunch.de}

---

## DealsXrunch — Deals & Business

{converted content from deals@m2.morningcrunch.de}
```

### Error Handling

| Situation | Behaviour |
|---|---|
| Neither email found | Return `None` — caller skips save, exits 0 |
| Only one email found | Return partial content with log warning; still save |
| IMAP connection error | Raise exception — caller exits 1 (Render logs failure) |
| HTML parse error | Log warning, fall back to `text/plain` MIME part if present |
| Email too old (>24h) | Log warning, skip that sender's email |

---

## `run_gmail_briefing.py`

```
1. check_env()  — abort if GMAIL_USERNAME or GMAIL_APP_PASSWORD missing
2. fetch_today_briefing()  → briefing_md: str | None
3. If None:  log("No emails found") + sys.exit(0)
4. Prepend header:  "# Daily Briefing — YYYY-MM-DD\n\n"
5. Write: outputs/latest-briefing.md       (overwrite)
6. Write: outputs/YYYY-MM-DD-briefing.md   (archive)
7. sync_to_brain(date, content)
8. Log success
```

---

## Render Deployment

### New Cron Service (render.yaml)

```yaml
- type: cron
  name: gmail-briefing-cron
  env: python
  plan: free
  schedule: "15 6 * * *"
  buildCommand: pip install -r requirements.txt
  startCommand: python -m scripts.run_gmail_briefing
```

Schedule: `15 6 * * *` = 06:15 UTC = 08:15 CEST.

### Required Render Environment Variables

Set on the `gmail-briefing-cron` service:

| Variable | Notes |
|---|---|
| `GMAIL_USERNAME` | Full Gmail address |
| `GMAIL_APP_PASSWORD` | 16-char App Password (mark as secret) |
| `GITHUB_TOKEN` | Same token as web service — needed by `sync_to_brain()` |
| `JULIO_BRAIN_OWNER` | Default: `juliokoelle` |
| `JULIO_BRAIN_REPO_NAME` | Default: `julio-brain` |

`ANTHROPIC_API_KEY` is **not** needed by the cron service (no LLM calls).

---

## API Changes (`api.py`)

`POST /briefing/generate` and `POST /generate-briefing` return:

```
HTTP 410 Gone
{
  "error": "generation_disabled",
  "message": "Briefing wird täglich automatisch per E-Mail bezogen."
}
```

---

## Frontend Changes (`frontend/index.html`)

Remove:
- `#generatePremiumBtn` ("Generate Premium" button)
- `#generateQuickBtn` ("Generate Quick" button)
- `#generateStatus` span
- `generateBriefing()` JS function

Replace buttons with static info text:
```
Briefing arrives daily at ~08:15 (CEST)
```

The rest of the briefing view (archive list, full-text display, PDF download) is unchanged.

---

## Dependencies

```
# requirements.txt — one new line:
html2text
```

`imaplib` and `email` are Python stdlib — no additional packages needed.

---

## Gmail Setup (one-time, manual)

Before deploying:
1. Gmail → Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP
2. Google Account → Security → 2-Step Verification → App passwords
3. Create App Password for "Mail" on "Other device" → name it "render-briefing"
4. Copy 16-char password → set as `GMAIL_APP_PASSWORD` on Render

---

## Out of Scope

- Email archiving or read/unread marking (emails remain as-is in Gmail)
- Retry logic if email arrives late (next day's cron handles the next email)
- Multiple Gmail accounts
- Attachment handling (both newsletters are HTML body only)
- Modifying the seven-section editorial structure of the briefing output
