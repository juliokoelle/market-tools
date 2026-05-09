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
from datetime import datetime, timedelta, timezone

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
    """Search INBOX (fallback: All Mail) for emails from sender within last 24 h.

    Uses SINCE yesterday so late-arriving or weekend editions are not missed.
    Returns the HTML body of the most recent match, or None if not found.
    """
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


def fetch_today_briefing() -> str | None:
    """Fetch today's newsletters from both MorningCrunch senders via IMAP.

    Returns combined Markdown string, or None if neither email was found.
    """
    conn = _connect_imap()
    sections: list[str] = []

    try:
        for sender_cfg in BRIEFING_SENDERS:
            sender = sender_cfg["from"]
            label  = sender_cfg["label"]
            html = _fetch_email_html(conn, sender)
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
