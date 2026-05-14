"""
Gmail briefing fetcher — IMAP + App Password.

Fetches today's emails from two MorningCrunch newsletters, converts HTML bodies
to Markdown, and returns a combined briefing string.

Env vars required:
    GMAIL_USERNAME      — full Gmail address (e.g. juliokoelle@gmail.com)
    GMAIL_APP_PASSWORD  — 16-char Google App Password (no spaces)
"""

from __future__ import annotations

import email as email_lib
import imaplib
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone

import html2text as ht

log = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

BRIEFING_SENDERS = [
    {
        "from":  "markets@m.morningcrunch.de",
        "label": "MarketsXrunch — Markets & Finance",
    },
    {
        "from":  "deals@m2.morningcrunch.de",
        "label": "DealsXrunch — Deals & Business",
    },
    {
        "from":  "thepapayanews@substack.com",
        "label": "Papaya News",
    },
]

_FOOTER_RE = re.compile(
    r"(Abmelde|Unsubscribe|©|\bImpressum\b|Datenschutz)",
    re.IGNORECASE,
)

# Lines that are pure table-structure noise: only pipes, dashes, or whitespace
_TABLE_LINE_RE = re.compile(r"^\s*[\|\-]+\s*$")

# Zero-width/invisible Unicode spacers used by email clients
_INVISIBLE_RE = re.compile(r"[​‌‍­﻿⁠]+")


def _preprocess_html(html: str) -> str:
    """Ensure table cells become separate lines; strip spacer/tracking-only cells."""
    # End each table cell with a line-break so adjacent cells don't concatenate
    html = re.sub(r"</t[dh]>", "</td>\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    return html


def _html_to_markdown(html: str) -> str:
    """Convert HTML email body to structured Markdown."""
    html = _preprocess_html(html)
    h = ht.HTML2Text()
    h.ignore_links  = True   # strip tracking URLs, keep link text
    h.ignore_images = True
    h.ignore_tables = True   # extract table cell text without pipe/dash syntax
    h.body_width    = 0
    h.unicode_snob  = True
    return h.handle(html)


def _clean_markdown(md: str) -> str:
    """Remove table artifacts, invisible chars, footers; collapse blank lines."""
    # Strip zero-width/invisible spacer characters
    md = _INVISIBLE_RE.sub("", md)

    lines = []
    for line in md.splitlines():
        # Drop footer lines
        if _FOOTER_RE.search(line):
            continue
        # Drop pure table-structure lines (| | |, ---, |---|)
        if _TABLE_LINE_RE.match(line):
            continue
        # Strip leading/trailing pipe characters left over from single-cell rows
        stripped = line.strip().strip("|").strip()
        # Drop lines that became empty or are just whitespace after stripping
        if not stripped and not line.strip():
            lines.append("")
            continue
        # Use the pipe-stripped version only if the original started/ended with |
        if line.strip().startswith("|") or line.strip().endswith("|"):
            lines.append(stripped)
        else:
            lines.append(line)

    text = "\n".join(lines)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_html(msg: email_lib.message.Message) -> str | None:
    """Walk MIME tree and return the first text/html payload as a decoded string."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    elif msg.get_content_type() == "text/html":
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return None


def _fetch_email_html(conn: imaplib.IMAP4_SSL, sender: str, target_date: date | None = None) -> str | None:
    """Search INBOX (fallback: All Mail) for emails from sender.

    If target_date is given, searches for emails ON that exact date (backfill).
    Otherwise searches SINCE yesterday (normal daily run).
    Returns the HTML body of the most recent match, or None if not found.
    """
    if target_date is not None:
        date_str  = target_date.strftime("%d-%b-%Y")
        criteria  = f'(FROM "{sender}" ON {date_str})'
    else:
        since_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%d-%b-%Y")
        criteria  = f'(FROM "{sender}" SINCE {since_str})'

    for mailbox in ("INBOX", '"[Gmail]/All Mail"'):
        typ, _ = conn.select(mailbox)
        if typ != "OK":
            continue

        typ, data = conn.search(None, criteria)
        if typ != "OK" or not data[0]:
            continue

        uids = data[0].split()
        if not uids:
            continue

        uid = uids[-1]  # most recent
        typ, msg_data = conn.fetch(uid, "(RFC822)")
        if typ != "OK":
            log.warning("[gmail] fetch failed for UID %s from %s", uid, sender)
            continue

        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)
        html = _extract_html(msg)
        if html is None:
            log.warning("[gmail] No HTML part found in email from %s", sender)
        return html

    return None


def _connect_imap() -> imaplib.IMAP4_SSL:
    """Open an authenticated IMAP connection. Raises on any failure."""
    username = os.environ["GMAIL_USERNAME"].strip()
    # Strip non-ASCII chars (e.g. \xa0 from copy-paste) that IMAP rejects
    password = os.environ["GMAIL_APP_PASSWORD"].encode("ascii", "ignore").decode("ascii").strip()
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(username, password)
    return conn


def fetch_today_briefing(target_date: date | None = None) -> str | None:
    """Fetch newsletters from BRIEFING_SENDERS via IMAP.

    target_date: specific date for backfill (ON search).
                 None = today's run (SINCE yesterday search).
    Returns combined Markdown string, or None if no email was found.
    """
    conn = _connect_imap()
    sections: list[str] = []

    try:
        for sender_cfg in BRIEFING_SENDERS:
            sender = sender_cfg["from"]
            label  = sender_cfg["label"]
            html = _fetch_email_html(conn, sender, target_date)
            if html is None:
                log.warning("[gmail] No email from %s today — skipping section.", sender)
                continue
            md = _clean_markdown(_html_to_markdown(html))
            sections.append(f"## {label}\n\n{md}")
            log.info("[gmail] Fetched %d chars from %s.", len(md), sender)
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    if not sections:
        return None

    return "\n\n---\n\n".join(sections)
