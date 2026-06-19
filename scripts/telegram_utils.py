"""Shared Telegram Bot API helpers for the non-PTB sender scripts.

morning_push and proactive_intelligence post directly to the Bot API (they have
no python-telegram-bot runtime). They previously sent parse_mode=Markdown with
raw or LLM-generated text, so any stray '_', '*', '[' or backtick made Telegram
reject the whole message (HTTP 400) and the delivery was lost.

send_message retries once in plain text on a parse error, so the message always
gets through even if the Markdown is malformed.
"""

from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)


def send_message(
    token: str,
    chat_id: str | int,
    text: str,
    parse_mode: str | None = "Markdown",
    timeout: float = 15,
) -> requests.Response:
    """Send a Telegram message, falling back to plain text if Markdown fails.

    Raises requests.HTTPError only when the plain-text send also fails.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    resp = requests.post(url, json=payload, timeout=timeout)
    if resp.status_code == 400 and parse_mode:
        log.warning(
            "Telegram %s parse failed (%s) — retrying as plain text",
            parse_mode,
            resp.text[:200],
        )
        payload.pop("parse_mode", None)
        resp = requests.post(url, json=payload, timeout=timeout)

    resp.raise_for_status()
    return resp
