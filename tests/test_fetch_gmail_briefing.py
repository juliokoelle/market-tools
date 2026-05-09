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


def test_fetch_email_html_searches_since_yesterday():
    """SINCE date must be yesterday so late-arriving emails are not missed."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import MagicMock, patch, call
    from scripts.fetch_gmail_briefing import _fetch_email_html
    conn = MagicMock()
    conn.select.return_value = ("OK", [b"1"])
    conn.search.return_value = ("OK", [b""])  # no results — we only check criteria

    fixed_now = datetime(2026, 5, 9, 7, 0, 0, tzinfo=timezone.utc)
    expected_since = "08-May-2026"  # yesterday

    with patch("scripts.fetch_gmail_briefing.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        _fetch_email_html(conn, "markets@m.morningcrunch.de")

    criteria_used = conn.search.call_args[0][1]
    assert expected_since in criteria_used


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


# ── fetch_today_briefing public API ──────────────────────────────────────────

def test_fetch_today_briefing_returns_none_when_no_emails():
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()
    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html", return_value=None):
        result = fetch_today_briefing()
    assert result is None
    mock_conn.logout.assert_called_once()


def test_fetch_today_briefing_combines_all_sections():
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()

    html_by_sender = {
        "markets": "<h2>Gold +1%</h2><p>DAX up.</p>",
        "deals":   "<h2>SAP Deal</h2><p>Acquisition closed.</p>",
        "papaya":  "<h2>Tech Roundup</h2><p>AI funding surge.</p>",
    }

    def fake_fetch(conn, sender):
        for key, html in html_by_sender.items():
            if key in sender:
                return html
        return None

    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html", side_effect=fake_fetch):
        result = fetch_today_briefing()

    assert result is not None
    assert "MarketsXrunch" in result
    assert "DealsXrunch" in result
    assert "Papaya News" in result
    assert result.index("MarketsXrunch") < result.index("DealsXrunch") < result.index("Papaya News")
    assert result.count("---") == 2  # two separators for three sections


def test_fetch_today_briefing_partial_returns_content():
    """Only one email found — return partial content, not None."""
    from unittest.mock import MagicMock, patch
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()

    def fake_fetch(conn, sender):
        return "<p>Markets content</p>" if "markets" in sender else None

    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html", side_effect=fake_fetch):
        result = fetch_today_briefing()

    assert result is not None
    assert "MarketsXrunch" in result
    assert "DealsXrunch" not in result


def test_fetch_today_briefing_closes_connection_on_error():
    from unittest.mock import MagicMock, patch
    import pytest
    from scripts.fetch_gmail_briefing import fetch_today_briefing
    mock_conn = MagicMock()

    with patch("scripts.fetch_gmail_briefing._connect_imap", return_value=mock_conn), \
         patch("scripts.fetch_gmail_briefing._fetch_email_html",
               side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            fetch_today_briefing()

    mock_conn.logout.assert_called_once()
