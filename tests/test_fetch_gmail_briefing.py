"""Unit tests for Gmail briefing fetcher."""
import email as email_lib
import pytest


def test_html_to_markdown_converts_headings():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<h2>Markets Today</h2><p>Gold rose 1.2% to $3,400/oz.</p>"
    result = _html_to_markdown(html)
    assert "## Markets Today" in result
    assert "Gold rose 1.2% to $3,400/oz." in result


def test_html_to_markdown_ignores_images():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<p>Text content</p><img src='track.gif' />"
    result = _html_to_markdown(html)
    assert "track.gif" not in result
    assert "Text content" in result


def test_html_to_markdown_preserves_umlauts():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<p>Märkte in Frankfurt stiegen um 0,5%.</p>"
    result = _html_to_markdown(html)
    assert "Märkte" in result
    assert "Frankfurt" in result


def test_html_to_markdown_preserves_bold():
    from scripts.fetch_gmail_briefing import _html_to_markdown
    html = "<p>DAX <strong>+1.2%</strong> today.</p>"
    result = _html_to_markdown(html)
    assert "**+1.2%**" in result


def test_clean_markdown_collapses_blank_lines():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Line 1\n\n\n\n\nLine 2"
    result = _clean_markdown(md)
    assert "\n\n\n" not in result
    assert "Line 1" in result
    assert "Line 2" in result


def test_clean_markdown_strips_abmelden():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Wichtige Nachricht hier.\n\nAbmelden von diesem Newsletter."
    result = _clean_markdown(md)
    assert "Wichtige Nachricht" in result
    assert "Abmelden" not in result


def test_clean_markdown_strips_unsubscribe_and_copyright():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Market update.\n\nUnsubscribe from this list.\n© 2026 MorningCrunch"
    result = _clean_markdown(md)
    assert "Market update." in result
    assert "Unsubscribe" not in result
    assert "© 2026" not in result


def test_clean_markdown_strips_impressum():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "Gute Neuigkeiten.\n\nImpressum | Datenschutz"
    result = _clean_markdown(md)
    assert "Gute Neuigkeiten." in result
    assert "Impressum" not in result


def test_clean_markdown_trims_whitespace():
    from scripts.fetch_gmail_briefing import _clean_markdown
    md = "\n\n  Content here.  \n\n"
    result = _clean_markdown(md)
    assert result == "Content here."


# ── IMAP fetch tests ─────────────────────────────────────────────────────────

def test_extract_html_from_simple_html_message():
    from email.mime.text import MIMEText
    from scripts.fetch_gmail_briefing import _extract_html
    raw = MIMEText("<h2>Gold +1%</h2>", "html", "utf-8").as_bytes()
    msg = email_lib.message_from_bytes(raw)
    result = _extract_html(msg)
    assert result is not None
    assert "Gold" in result


def test_extract_html_from_multipart_message():
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from scripts.fetch_gmail_briefing import _extract_html
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("Plain text version", "plain", "utf-8"))
    msg.attach(MIMEText("<p>HTML version</p>", "html", "utf-8"))
    result = _extract_html(email_lib.message_from_bytes(msg.as_bytes()))
    assert result is not None
    assert "HTML version" in result


def test_extract_html_returns_none_for_plain_only():
    from email.mime.text import MIMEText
    from scripts.fetch_gmail_briefing import _extract_html
    msg = email_lib.message_from_bytes(
        MIMEText("Plain only", "plain", "utf-8").as_bytes()
    )
    result = _extract_html(msg)
    assert result is None


def test_fetch_email_html_returns_none_when_search_empty():
    from unittest.mock import MagicMock
    from scripts.fetch_gmail_briefing import _fetch_email_html
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b""])  # no results
    result = _fetch_email_html(conn, "markets@m.morningcrunch.de")
    assert result is None


def test_fetch_email_html_returns_html_body():
    from email.mime.text import MIMEText
    from unittest.mock import MagicMock
    from scripts.fetch_gmail_briefing import _fetch_email_html
    raw  = MIMEText("<h2>Markets Today</h2>", "html", "utf-8").as_bytes()
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b"42"])
    conn.fetch.return_value  = ("OK", [(b"42 (RFC822 {256})", raw)])
    result = _fetch_email_html(conn, "markets@m.morningcrunch.de")
    assert result is not None
    assert "Markets Today" in result


def test_fetch_email_html_takes_last_uid_when_multiple():
    """When multiple UIDs match, fetch the last (most recent) one."""
    from email.mime.text import MIMEText
    from unittest.mock import MagicMock
    from scripts.fetch_gmail_briefing import _fetch_email_html
    raw  = MIMEText("<p>Latest</p>", "html", "utf-8").as_bytes()
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"5"])
    conn.search.return_value = ("OK", [b"10 11 12"])
    conn.fetch.return_value  = ("OK", [(b"12 (RFC822 {100})", raw)])
    _fetch_email_html(conn, "markets@m.morningcrunch.de")
    conn.fetch.assert_called_once_with(b"12", "(RFC822)")
