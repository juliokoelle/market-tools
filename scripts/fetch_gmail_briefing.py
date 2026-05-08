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
from datetime import datetime, timezone

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
]

_FOOTER_RE = re.compile(
    r"(Abmelde|Unsubscribe|©|\bImpressum\b|Datenschutz)",
    re.IGNORECASE,
)


def _html_to_markdown(html: str) -> str:
    """Convert HTML email body to structured Markdown."""
    h = ht.HTML2Text()
    h.ignore_links  = False
    h.ignore_images = True
    h.body_width    = 0
    h.unicode_snob  = True
    return h.handle(html)


def _clean_markdown(md: str) -> str:
    """Strip footer boilerplate and collapse excessive blank lines."""
    lines = [line for line in md.splitlines() if not _FOOTER_RE.search(line)]
    text  = "\n".join(lines)
    text  = re.sub(r"\n{3,}", "\n\n", text)
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


def _fetch_email_html(conn: imaplib.IMAP4_SSL, sender: str) -> str | None:
    """Search INBOX (fallback: All Mail) for today's email from sender.

    Returns the HTML body of the most recent match, or None if not found.
    """
    today_str = datetime.now(timezone.utc).strftime("%d-%b-%Y")  # e.g. "08-May-2026"
    criteria  = f'(FROM "{sender}" SINCE {today_str})'

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
    username = os.environ["GMAIL_USERNAME"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(username, password)
    return conn
