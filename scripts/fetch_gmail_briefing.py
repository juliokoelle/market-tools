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
